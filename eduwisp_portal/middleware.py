# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Michele Salerno e i contributori di EduWISP
from django.conf import settings
from django.shortcuts import render
from django.urls import reverse

from .vista import SESSION_VEDI_COME

METODI_SICURI = {"GET", "HEAD", "OPTIONS"}


def is_read_only_account(user):
    """Account in sola lettura, per esempio l'utente «demo» dell'ambiente di prova."""
    gruppo = getattr(settings, "EDUWISP_READ_ONLY_GROUP", "sola-lettura")
    return user is not None and user.is_authenticated and user.groups.filter(name=gruppo).exists()


class SolaLetturaVediComeMiddleware:
    """Durante il «vedi come», e per gli account in sola lettura, nessuna modifica è possibile.

    Vale in ogni parte del sito, compresa l'amministrazione di Django. Restano permessi solo
    l'uscita dall'account, l'inizio e la fine del «vedi come» (che è a sua volta in sola
    lettura e registrato). Va messo dopo SessionMiddleware e AuthenticationMiddleware.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method not in METODI_SICURI:
            uscite = (reverse("eduwisp_portal:vedi_come_esci"), reverse("eduwisp_portal:esci"))
            if SESSION_VEDI_COME in request.session and request.path not in uscite:
                return render(request, "eduwisp_portal/sola_lettura.html", status=403)
            permessi = (*uscite, reverse("eduwisp_portal:vedi_come"))
            if is_read_only_account(request.user) and request.path not in permessi:
                return render(request, "eduwisp_portal/sola_lettura.html", status=403)
        return self.get_response(request)
