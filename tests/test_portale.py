# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Michele Salerno e i contributori di EduWISP
import pytest
from eduwisp_audit.models import Action, AuditEvent
from eduwisp_users.models import Organization

pytestmark = pytest.mark.django_db


def test_anonimo_va_all_accesso(client):
    r = client.get("/")
    assert r.status_code == 302 and r.url.startswith("/accedi/")


def test_amministratore_vede_tutti_gli_istituti(client, scuola, admin_user):
    Organization.objects.create(name="Istituto Due", slug="due")
    client.force_login(admin_user)
    r = client.get("/", follow=True)
    testo = r.content.decode()
    assert "Amministrazione della piattaforma" in testo
    assert "Liceo Fittizio" in testo and "Istituto Due" in testo
    assert "Aggiungi un istituto" in testo and "Vedi come" in testo


def test_area_amministrazione_nascosta_agli_altri(client, scuola):
    client.force_login(scuola["preside"])
    assert client.get("/amministrazione/").status_code == 404
    assert client.get("/vedi-come/").status_code == 404
    assert "Vedi come" not in client.get("/preside/").content.decode()


def test_preside_vede_tutto_l_istituto(client, scuola):
    client.force_login(scuola["preside"])
    r = client.get("/", follow=True)
    assert r.request["PATH_INFO"] == "/preside/"
    assert client.get(f"/classe/{scuola['c1b'].pk}/").status_code == 200


def test_docente_vede_solo_le_sue_classi(client, scuola):
    client.force_login(scuola["docente"])
    testo = client.get("/docente/").content.decode()
    assert "Matematica" in testo
    assert f"/classe/{scuola['c1a'].pk}/" in testo
    assert f"/classe/{scuola['c1b'].pk}/" not in testo
    assert "Rossi Anna" in client.get(f"/classe/{scuola['c1a'].pk}/").content.decode()
    assert client.get(f"/classe/{scuola['c1b'].pk}/").status_code == 404
    assert AuditEvent.objects.filter(action=Action.ACCESS_DENIED).count() == 1
    assert client.get("/preside/").status_code == 404


def test_famiglia_vede_solo_il_proprio_figlio(client, scuola):
    client.force_login(scuola["genitore"])
    testo = client.get("/famiglia/").content.decode()
    assert "Rossi Anna" in testo and "Bianchi Luca" not in testo
    assert client.get(f"/classe/{scuola['c1a'].pk}/").status_code == 404
    assert client.get("/docente/").status_code == 404


def test_vedi_come_chiede_il_motivo_sui_dati_reali(client, scuola, admin_user):
    client.force_login(admin_user)
    r = client.post("/vedi-come/", {"ruolo": "teacher", "membership": scuola["m_docente"].pk})
    assert r.status_code == 200 and "Indica il motivo" in r.content.decode()
    assert not AuditEvent.objects.exists()


def test_vedi_come_in_sola_lettura_e_registrato(client, scuola, admin_user):
    client.force_login(admin_user)
    r = client.post(
        "/vedi-come/",
        {"ruolo": "teacher", "membership": scuola["m_docente"].pk, "motivo": "assistenza 42"},
    )
    assert r.status_code == 302
    inizio = AuditEvent.objects.get(action=Action.VIEW_AS_START)
    assert inizio.actor == admin_user and inizio.subject == scuola["docente"]
    assert inizio.reason == "assistenza 42"

    testo = client.get("/", follow=True).content.decode()
    assert "Stai vedendo come" in testo and "Sola lettura" in testo
    assert f"/classe/{scuola['c1b'].pk}/" not in testo  # vede solo ciò che vede il docente
    assert client.get("/amministrazione/").status_code == 302

    # Nessuna modifica possibile, nemmeno nell'amministrazione di Django
    r = client.post("/admin/eduwisp_users/organization/add/", {"name": "X", "slug": "x"})
    assert r.status_code == 403
    assert not Organization.objects.filter(slug="x").exists()

    # Fuori ambito durante la vista: 404 registrato con la persona simulata
    assert client.get(f"/classe/{scuola['c1b'].pk}/").status_code == 404
    negato = AuditEvent.objects.get(action=Action.ACCESS_DENIED)
    assert negato.actor == admin_user and negato.subject == scuola["docente"]

    assert client.post("/vedi-come/esci/").status_code == 302
    fine = AuditEvent.objects.get(action=Action.VIEW_AS_STOP)
    assert "durata_secondi" in fine.details
    assert "Amministrazione della piattaforma" in client.get("/", follow=True).content.decode()


def test_vedi_come_famiglia_nella_demo_senza_motivo(client, scuola, admin_user, settings):
    settings.EDUWISP_ENVIRONMENT_NOTICE = "Ambiente di prova"
    client.force_login(admin_user)
    r = client.post("/vedi-come/", {"ruolo": "guardian", "membership": scuola["m_genitore"].pk})
    assert r.status_code == 302
    testo = client.get("/", follow=True).content.decode()
    assert "Rossi Anna" in testo and "Bianchi Luca" not in testo


def test_uscita_dall_account_chiude_la_vista(client, scuola, admin_user, settings):
    settings.EDUWISP_ENVIRONMENT_NOTICE = "Ambiente di prova"
    client.force_login(admin_user)
    client.post("/vedi-come/", {"ruolo": "school_admin", "membership": scuola["m_preside"].pk})
    assert client.post("/esci/").status_code == 302
    assert AuditEvent.objects.filter(action=Action.VIEW_AS_STOP).count() == 1


def test_chi_ha_piu_ruoli_sceglie(client, scuola):
    from eduwisp_school.models import Guardian
    from eduwisp_users.models import Membership, Role

    docente = scuola["docente"]
    m = Membership.objects.create(
        user=docente,
        organization=Organization.objects.create(name="Altro", slug="altro"),
        role=Role.GUARDIAN,
    )
    client.force_login(docente)
    assert client.get("/", follow=True).request["PATH_INFO"] == "/docente/"
    client.post("/ruolo/", {"membership": m.pk})
    assert client.get("/", follow=True).request["PATH_INFO"] == "/famiglia/"
    assert Guardian.objects.filter(user=docente).count() == 0


def test_famiglia_e_figlio_maggiorenne(client, scuola):
    from datetime import date

    figlio = scuola["figlio"]
    figlio.adult_on = date(2000, 1, 1)
    figlio.save()
    client.force_login(scuola["genitore"])
    testo = client.get("/famiglia/").content.decode()
    assert "Rossi Anna" in testo and "È maggiorenne" in testo
    assert "Dispositivi della scuola" not in testo
    figlio.family_access_granted = True
    figlio.save()
    testo = client.get("/famiglia/").content.decode()
    assert "Dispositivi della scuola" in testo and "È maggiorenne" not in testo


@pytest.fixture
def catalogo(scuola):
    from eduwisp_apps.models import App, AppRule

    org = scuola["org"]
    firefox = App.objects.create(
        organization=org, name="Browser di prova", identifier="org.example.browser"
    )
    wiki = App.objects.create(
        organization=org, name="Enciclopedia", identifier="org.example.enciclopedia"
    )
    AppRule.objects.create(organization=org, app=firefox)
    return {"firefox": firefox, "wiki": wiki}


def test_docente_sblocca_e_richiude_un_app(client, scuola, catalogo):
    from eduwisp_apps.models import TemporaryUnlock

    client.force_login(scuola["docente"])
    url = f"/classe/{scuola['c1a'].pk}/"
    testo = client.get(url).content.decode()
    assert (
        "Browser di prova" in testo
        and "Microsoft Teams" in testo
        and "Sblocca per la lezione" in testo
    )
    r = client.post(url + "sblocca/", {"app": catalogo["wiki"].pk, "minuti": 60}, follow=True)
    assert "Enciclopedia sbloccata per 60 minuti" in r.content.decode()
    s = TemporaryUnlock.objects.get()
    assert s.school_class == scuola["c1a"] and s.teacher == scuola["docente"]
    assert AuditEvent.objects.filter(action=Action.APP_UNLOCK).count() == 1
    r = client.post(f"/sblocco/{s.pk}/termina/", follow=True)
    assert "di nuovo bloccata" in r.content.decode()
    s.refresh_from_db()
    assert s.ended_early_at is not None


def test_docente_non_sblocca_in_altre_classi(client, scuola, catalogo):
    client.force_login(scuola["docente"])
    r = client.post(
        f"/classe/{scuola['c1b'].pk}/sblocca/", {"app": catalogo["wiki"].pk, "minuti": 60}
    )
    assert r.status_code == 404
    assert not AuditEvent.objects.filter(action=Action.APP_UNLOCK).exists()


def test_durata_non_prevista_rifiutata(client, scuola, catalogo):
    from eduwisp_apps.models import TemporaryUnlock

    client.force_login(scuola["docente"])
    client.post(f"/classe/{scuola['c1a'].pk}/sblocca/", {"app": catalogo["wiki"].pk, "minuti": 600})
    assert not TemporaryUnlock.objects.exists()


def test_preside_vede_le_app_ma_non_sblocca(client, scuola, catalogo):
    client.force_login(scuola["preside"])
    testo = client.get(f"/classe/{scuola['c1a'].pk}/").content.decode()
    assert "Browser di prova" in testo and "Sblocca per la lezione" not in testo
    r = client.post(
        f"/classe/{scuola['c1a'].pk}/sblocca/", {"app": catalogo["wiki"].pk, "minuti": 60}
    )
    assert r.status_code == 404


def test_vedi_come_docente_non_sblocca(client, scuola, catalogo, admin_user, settings):
    from eduwisp_apps.models import TemporaryUnlock

    settings.EDUWISP_ENVIRONMENT_NOTICE = "Ambiente di prova"
    client.force_login(admin_user)
    client.post("/vedi-come/", {"ruolo": "teacher", "membership": scuola["m_docente"].pk})
    r = client.post(
        f"/classe/{scuola['c1a'].pk}/sblocca/", {"app": catalogo["wiki"].pk, "minuti": 60}
    )
    assert r.status_code == 403
    assert not TemporaryUnlock.objects.exists()


def test_account_demo_in_sola_lettura(client, scuola, settings):
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Group

    settings.EDUWISP_ENVIRONMENT_NOTICE = "Ambiente di prova"
    demo = get_user_model().objects.create_superuser("demo", password="demo")
    demo.groups.add(Group.objects.create(name="sola-lettura"))
    assert client.login(username="demo", password="demo")
    testo = client.get("/", follow=True).content.decode()
    assert "in sola lettura" in testo and "Amministrazione della piattaforma" in testo
    # Nessuna modifica, nemmeno nell'amministrazione di Django
    r = client.post("/admin/eduwisp_users/organization/add/", {"name": "X", "slug": "x"})
    assert r.status_code == 403 and not Organization.objects.filter(slug="x").exists()
    assert client.post("/admin/password_change/", {}).status_code == 403
    # Il «vedi come» resta possibile, in sola lettura
    r = client.post("/vedi-come/", {"ruolo": "teacher", "membership": scuola["m_docente"].pk})
    assert r.status_code == 302
    assert "Stai vedendo come" in client.get("/", follow=True).content.decode()
    assert client.post("/vedi-come/esci/").status_code == 302
    assert client.post("/esci/").status_code == 302


def test_pagina_di_accesso_indica_l_utente_demo(client, db, settings):
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Group

    assert "utente <strong>demo</strong>" not in client.get("/accedi/").content.decode()
    demo = get_user_model().objects.create_user("demo", password="demo")
    demo.groups.add(Group.objects.create(name="sola-lettura"))
    assert "utente <strong>demo</strong>" not in client.get("/accedi/").content.decode()
    settings.EDUWISP_ENVIRONMENT_NOTICE = "Ambiente di prova"
    assert "utente <strong>demo</strong>" in client.get("/accedi/").content.decode()
