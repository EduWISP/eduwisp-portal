# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Michele Salerno e i contributori di EduWISP
"""Chi sta guardando e con quale ruolo (ADR-0018).

Ogni pagina usa una «vista»: la persona di cui si mostrano i dati, il ruolo e l'istituto.
Di solito è l'utente stesso. Con il «vedi come» l'amministratore di sistema guarda come
un'altra persona, in sola lettura; inizio e fine sono registrati in eduwisp-audit.
"""

from dataclasses import dataclass

from django.utils import timezone
from eduwisp_audit.log import record
from eduwisp_audit.models import Action
from eduwisp_users.models import Membership, Role

SESSION_VEDI_COME = "eduwisp_vedi_come"
SESSION_RUOLO = "eduwisp_ruolo"

# Ruoli con una propria area nel portale, nell'ordine del menu «Vedi come».
RUOLI = {
    Role.SCHOOL_ADMIN: ("Dirigente (preside)", "eduwisp_portal:preside"),
    Role.TEACHER: ("Docente", "eduwisp_portal:docente"),
    Role.GUARDIAN: ("Famiglia", "eduwisp_portal:famiglia"),
}


@dataclass
class Vista:
    viewer: object  # chi è davvero collegato
    user: object  # di chi si mostrano i dati
    membership: Membership | None
    vedi_come: bool = False
    motivo: str = ""

    @property
    def role(self):
        return self.membership.role if self.membership else None

    @property
    def organization(self):
        return self.membership.organization if self.membership else None

    @property
    def role_label(self):
        return RUOLI[self.role][0] if self.role in RUOLI else ""


def appartenenze(user):
    return list(
        Membership.objects.select_related("organization")
        .filter(user=user, role__in=list(RUOLI), organization__is_active=True)
        .order_by("organization__name")
    )


def vista_corrente(request):
    user = request.user
    dati = request.session.get(SESSION_VEDI_COME)
    if dati and user.is_superuser:
        m = (
            Membership.objects.select_related("user", "organization")
            .filter(pk=dati["membership"])
            .first()
        )
        if m is not None:
            return Vista(user, m.user, m, vedi_come=True, motivo=dati.get("motivo", ""))
        chiudi_vedi_come(request, user, motivo_chiusura="persona non più disponibile")
    elenco = appartenenze(user)
    scelta = request.session.get(SESSION_RUOLO)
    priorita = list(RUOLI)
    elenco.sort(key=lambda m: (m.pk != scelta, priorita.index(m.role)))
    return Vista(user, user, elenco[0] if elenco else None)


def apri_vedi_come(request, membership, motivo):
    request.session[SESSION_VEDI_COME] = {
        "membership": membership.pk,
        "motivo": motivo,
        "inizio": timezone.now().isoformat(),
    }
    record(
        Action.VIEW_AS_START,
        actor=request.user,
        organization=membership.organization,
        subject=membership.user,
        reason=motivo,
        ruolo=membership.role,
    )


def chiudi_vedi_come(request, user, motivo_chiusura=""):
    dati = request.session.pop(SESSION_VEDI_COME, None)
    if not dati:
        return
    m = (
        Membership.objects.select_related("user", "organization")
        .filter(pk=dati["membership"])
        .first()
    )
    inizio = timezone.datetime.fromisoformat(dati["inizio"])
    durata = int((timezone.now() - inizio).total_seconds())
    record(
        Action.VIEW_AS_STOP,
        actor=user,
        organization=m.organization if m else None,
        subject=m.user if m else None,
        reason=dati.get("motivo", ""),
        durata_secondi=durata,
        chiusura=motivo_chiusura,
    )
