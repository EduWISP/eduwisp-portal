# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Michele Salerno e i contributori di EduWISP
from .middleware import is_read_only_account
from .vista import RUOLI, appartenenze, vista_corrente


def portale(request):
    """Vista corrente e voci del menu «Vedi come» per i template del portale."""
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {"accesso_demo": _accesso_demo()}
    vista = vista_corrente(request)
    return {
        "vista": vista,
        "sola_lettura": is_read_only_account(request.user),
        "richieste_in_attesa": _richieste_in_attesa(vista),
        "mie_appartenenze": [] if vista.vedi_come else appartenenze(request.user),
        "ruoli_vedi_come": [(r, etichetta) for r, (etichetta, _) in RUOLI.items()],
    }


def _accesso_demo():
    """Nella pagina di accesso degli ambienti di prova si indica l'utente pubblico «demo»."""
    from django.conf import settings
    from django.contrib.auth import get_user_model

    if not getattr(settings, "EDUWISP_ENVIRONMENT_NOTICE", ""):
        return False
    gruppo = getattr(settings, "EDUWISP_READ_ONLY_GROUP", "sola-lettura")
    return get_user_model().objects.filter(username="demo", groups__name=gruppo).exists()


def _richieste_in_attesa(vista):
    """Numero di richieste di app in attesa visibili alla persona (ADR-0021)."""
    from eduwisp_apps.models import RequestStatus
    from eduwisp_apps.requests import visible_requests
    from eduwisp_users.models import Role

    if vista.role not in (Role.SCHOOL_ADMIN, Role.TEACHER, Role.GUARDIAN):
        return None
    return (
        visible_requests(vista.user, vista.role, vista.organization)
        .filter(status=RequestStatus.IN_ATTESA)
        .count()
    )
