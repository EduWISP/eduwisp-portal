# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Michele Salerno e i contributori di EduWISP
"""Pagine del portale per ruolo (ADR-0018). I permessi si controllano qui, sul server."""

from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from eduwisp_apps.models import AppRule, TemporaryUnlock
from eduwisp_apps.unlocks import (
    DURATE_MINUTI,
    active_unlocks,
    allowed_apps_for_class,
    end_unlock,
    unlock,
    unlockable_apps,
)
from eduwisp_audit.log import record
from eduwisp_audit.models import Action
from eduwisp_devices.models import Device, DeviceAssignment
from eduwisp_school.models import (
    Guardian,
    SchoolClass,
    Student,
    StudentEnrollment,
    TeachingAssignment,
)
from eduwisp_school.queries import classes_for_teacher, linked_students, students_for_guardian
from eduwisp_users.models import Membership, Organization, Role

from .vista import RUOLI, SESSION_RUOLO, apri_vedi_come, chiudi_vedi_come, vista_corrente

ORE_SENZA_CONTATTO = 24
MAX_PERSONE = 300


def _richiede_admin(request):
    if not request.user.is_superuser:
        raise Http404


def _vista_con_ruolo(request, role):
    vista = vista_corrente(request)
    if vista.role != role:
        raise Http404
    return vista


def _fuori_ambito(vista, cosa):
    """Accesso fuori dal proprio ambito: risposta 404 e registrazione (ADR-0018)."""
    record(
        Action.ACCESS_DENIED,
        actor=vista.viewer,
        organization=vista.organization,
        subject=vista.user if vista.vedi_come else None,
        risorsa=cosa,
        vedi_come=vista.vedi_come,
    )
    raise Http404


def _riepilogo_classi(classi):
    classi = list(classi.select_related("section", "section__track"))
    studenti = dict(
        StudentEnrollment.objects.filter(school_class__in=classi)
        .values_list("school_class")
        .annotate(n=Count("id"))
    )
    limite = timezone.now() - timedelta(hours=ORE_SENZA_CONTATTO)
    dispositivi = {
        r["school_class"]: r
        for r in DeviceAssignment.objects.filter(school_class__in=classi, ended_at__isnull=True)
        .values("school_class")
        .annotate(
            totale=Count("id"),
            non_conformi=Count("id", filter=Q(device__compliant=False)),
            senza_contatto=Count(
                "id",
                filter=Q(device__last_seen_at__lt=limite) | Q(device__last_seen_at__isnull=True),
            ),
        )
    }
    righe = []
    for c in classi:
        d = dispositivi.get(c.pk, {})
        righe.append(
            {
                "classe": c,
                "studenti": studenti.get(c.pk, 0),
                "dispositivi": d.get("totale", 0),
                "non_conformi": d.get("non_conformi", 0),
                "senza_contatto": d.get("senza_contatto", 0),
            }
        )
    return righe


def _totali(righe):
    return {k: sum(r[k] for r in righe) for k in ("studenti", "dispositivi", "non_conformi")}


@login_required
def home(request):
    vista = vista_corrente(request)
    if request.user.is_superuser and not vista.vedi_come:
        return redirect("eduwisp_portal:amministrazione")
    if vista.role not in RUOLI:
        return render(request, "eduwisp_portal/nessun_ruolo.html")
    return redirect(RUOLI[vista.role][1])


@login_required
@require_POST
def scegli_ruolo(request):
    """Chi ha più ruoli (per esempio docente e genitore) sceglie quale usare."""
    pk = int(request.POST.get("membership", 0))
    if Membership.objects.filter(pk=pk, user=request.user, role__in=list(RUOLI)).exists():
        request.session[SESSION_RUOLO] = pk
    return redirect("eduwisp_portal:home")


@login_required
def amministrazione(request):
    _richiede_admin(request)
    if vista_corrente(request).vedi_come:
        return redirect("eduwisp_portal:home")

    def per_istituto(qs):
        return dict(qs.values_list("organization").annotate(n=Count("id")).order_by())

    classi = per_istituto(SchoolClass.objects.filter(school_year__is_current=True))
    studenti = per_istituto(Student.objects.all())
    dispositivi = per_istituto(Device.objects.filter(is_retired=False))
    istituti = [
        {
            "istituto": o,
            "classi": classi.get(o.pk, 0),
            "studenti": studenti.get(o.pk, 0),
            "dispositivi": dispositivi.get(o.pk, 0),
        }
        for o in Organization.objects.order_by("name")
    ]
    persone = dict(Membership.objects.values_list("role").annotate(n=Count("id")).order_by())
    return render(
        request,
        "eduwisp_portal/amministrazione.html",
        {
            "istituti": istituti,
            "persone": [(etichetta, persone.get(r, 0)) for r, (etichetta, _) in RUOLI.items()],
            "amministratori_it": persone.get(Role.IT_ADMIN, 0),
        },
    )


@login_required
def vedi_come(request):
    """Menu «Vedi come»: ruolo, poi persona; in sola lettura e registrato (ADR-0018)."""
    _richiede_admin(request)
    if vista_corrente(request).vedi_come:
        return redirect("eduwisp_portal:home")
    demo = bool(getattr(settings, "EDUWISP_ENVIRONMENT_NOTICE", ""))
    ruolo = request.POST.get("ruolo") or request.GET.get("ruolo") or Role.SCHOOL_ADMIN
    if ruolo not in RUOLI:
        raise Http404
    errore = ""
    if request.method == "POST":
        motivo = request.POST.get("motivo", "").strip()
        m = (
            Membership.objects.select_related("user", "organization")
            .filter(pk=request.POST.get("membership") or 0, role=ruolo)
            .first()
        )
        if m is None:
            errore = "Scegli una persona."
        elif not motivo and not demo:
            errore = "Indica il motivo: i dati sono reali e l'accesso viene registrato."
        else:
            apri_vedi_come(request, m, motivo)
            return redirect("eduwisp_portal:home")
    cerca = request.GET.get("cerca", "").strip()
    persone = Membership.objects.select_related("user", "organization").filter(
        role=ruolo, organization__is_active=True
    )
    if request.GET.get("istituto"):
        persone = persone.filter(organization_id=request.GET["istituto"])
    if cerca:
        persone = persone.filter(
            Q(user__first_name__icontains=cerca)
            | Q(user__last_name__icontains=cerca)
            | Q(user__username__icontains=cerca)
        )
    totale = persone.count()
    persone = persone.order_by("user__last_name", "user__first_name", "organization__name")
    return render(
        request,
        "eduwisp_portal/vedi_come.html",
        {
            "ruolo": ruolo,
            "ruolo_label": RUOLI[ruolo][0],
            "persone": persone[:MAX_PERSONE],
            "totale": totale,
            "troncato": totale > MAX_PERSONE,
            "cerca": cerca,
            "istituti": Organization.objects.filter(is_active=True).order_by("name"),
            "istituto": request.GET.get("istituto", ""),
            "demo": demo,
            "errore": errore,
        },
    )


@login_required
@require_POST
def vedi_come_esci(request):
    chiudi_vedi_come(request, request.user, motivo_chiusura="uscita dalla vista")
    return redirect("eduwisp_portal:amministrazione")


@login_required
def preside(request):
    vista = _vista_con_ruolo(request, Role.SCHOOL_ADMIN)
    classi = SchoolClass.objects.filter(
        organization=vista.organization, school_year__is_current=True
    ).order_by("section__name", "year_number")
    righe = _riepilogo_classi(classi)
    docenti = Membership.objects.filter(organization=vista.organization, role=Role.TEACHER)
    return render(
        request,
        "eduwisp_portal/preside.html",
        {"righe": righe, "totali": _totali(righe), "docenti": docenti.count()},
    )


@login_required
def docente(request):
    vista = _vista_con_ruolo(request, Role.TEACHER)
    classi = classes_for_teacher(vista.user).filter(organization=vista.organization)
    incarichi = (
        TeachingAssignment.objects.filter(
            teacher=vista.user,
            organization=vista.organization,
            school_year__is_current=True,
        )
        .select_related("section", "school_class")
        .order_by("section__name", "school_class__year_number")
    )
    righe = _riepilogo_classi(classi.order_by("section__name", "year_number"))
    return render(
        request,
        "eduwisp_portal/docente.html",
        {"righe": righe, "totali": _totali(righe), "incarichi": incarichi},
    )


def obbligatorie_della_classe(c):
    """Pk delle app del catalogo dell'istituto obbligatorie per la classe (ADR-0020)."""
    ambito = Q(track__isnull=True, school_class__isnull=True) | Q(school_class=c)
    if c.section.track_id:
        ambito |= Q(track_id=c.section.track_id)
    return set(
        AppRule.objects.filter(ambito, organization=c.organization, required=True).values_list(
            "app_id", flat=True
        )
    )


def _classe_consentita(vista, pk):
    if vista.role == Role.SCHOOL_ADMIN:
        consentite = SchoolClass.objects.filter(organization=vista.organization)
    elif vista.role == Role.TEACHER:
        consentite = classes_for_teacher(vista.user).filter(organization=vista.organization)
    else:
        consentite = SchoolClass.objects.none()
    c = consentite.select_related("section", "school_year").filter(pk=pk).first()
    if c is None:
        _fuori_ambito(vista, f"classe {pk}")
    return c


@login_required
def classe(request, pk):
    vista = vista_corrente(request)
    c = _classe_consentita(vista, pk)
    studenti = Student.objects.filter(enrollments__school_class=c).order_by("display_name")
    assegnazioni = (
        DeviceAssignment.objects.filter(school_class=c, ended_at__isnull=True)
        .select_related("device", "student")
        .order_by("device__display_name")
    )
    personali = {a.student_id: a.device for a in assegnazioni if a.student_id}
    return render(
        request,
        "eduwisp_portal/classe.html",
        {
            "classe": c,
            "studenti": [(s, personali.get(s.pk)) for s in studenti],
            "condivisi": [a.device for a in assegnazioni if not a.student_id],
            "limite": timezone.now() - timedelta(hours=ORE_SENZA_CONTATTO),
            "app_consentite": allowed_apps_for_class(c),
            "obbligatorie": obbligatorie_della_classe(c),
            "sblocchi": active_unlocks(c),
            "app_sbloccabili": unlockable_apps(c).order_by("name")
            if vista.role == Role.TEACHER
            else [],
            "durate": DURATE_MINUTI,
        },
    )


@login_required
@require_POST
def sblocca_app(request, pk):
    """Il docente sblocca un'app del catalogo per una delle sue classi (ADR-0019)."""
    vista = _vista_con_ruolo(request, Role.TEACHER)
    c = _classe_consentita(vista, pk)
    app = unlockable_apps(c).filter(pk=request.POST.get("app") or 0).first()
    try:
        minuti = int(request.POST.get("minuti", 0))
    except ValueError:
        minuti = 0
    if app is None or minuti not in DURATE_MINUTI:
        messages.error(request, "Scegli un'app e una durata.")
    else:
        try:
            unlock(vista.user, c, app, minuti)
            messages.success(request, f"{app.name} sbloccata per {minuti} minuti.")
        except (PermissionDenied, ValidationError) as e:
            messages.error(request, " ".join(getattr(e, "messages", [str(e)])))
    return redirect("eduwisp_portal:classe", pk=c.pk)


@login_required
@require_POST
def termina_sblocco(request, pk):
    vista = _vista_con_ruolo(request, Role.TEACHER)
    sblocco = (
        TemporaryUnlock.objects.select_related("school_class", "app")
        .filter(pk=pk, organization=vista.organization)
        .first()
    )
    if sblocco is None:
        _fuori_ambito(vista, f"sblocco {pk}")
    c = _classe_consentita(vista, sblocco.school_class_id)
    end_unlock(vista.user, sblocco)
    messages.success(request, f"{sblocco.app.name} di nuovo bloccata.")
    return redirect("eduwisp_portal:classe", pk=c.pk)


@login_required
def famiglia(request):
    vista = _vista_con_ruolo(request, Role.GUARDIAN)
    figli = students_for_guardian(vista.user).filter(organization=vista.organization)
    schede = []
    for figlio in figli.order_by("display_name"):
        iscrizione = (
            StudentEnrollment.objects.filter(
                student=figlio, school_class__school_year__is_current=True
            )
            .select_related("school_class__section")
            .first()
        )
        dispositivi = Device.objects.filter(
            assignments__student=figlio, assignments__ended_at__isnull=True
        ).distinct()
        relazione = Guardian.objects.filter(user=vista.user, student=figlio).first()
        schede.append(
            {
                "studente": figlio,
                "classe": iscrizione.school_class if iscrizione else None,
                "dispositivi": dispositivi,
                "relazione": relazione,
            }
        )
    # Maggiorenni senza consenso: solo il nome, nessun dato (ADR-0018).
    visibili = {f.pk for f in figli}
    maggiorenni = [
        s
        for s in linked_students(vista.user).filter(organization=vista.organization)
        if s.pk not in visibili
    ]
    return render(
        request,
        "eduwisp_portal/famiglia.html",
        {
            "schede": schede,
            "maggiorenni": maggiorenni,
            "limite": timezone.now() - timedelta(hours=ORE_SENZA_CONTATTO),
        },
    )
