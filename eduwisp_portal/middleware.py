# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Michele Salerno e i contributori di EduWISP
from django.shortcuts import render
from django.urls import reverse

from .vista import SESSION_VEDI_COME

METODI_SICURI = {"GET", "HEAD", "OPTIONS"}


class SolaLetturaVediComeMiddleware:
    """Durante il «vedi come» nessuna modifica è possibile, in nessuna parte del sito.

    Restano permessi solo l'uscita dalla vista e l'uscita dall'account. Va messo dopo
    SessionMiddleware e AuthenticationMiddleware.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.method not in METODI_SICURI
            and SESSION_VEDI_COME in request.session
            and request.path
            not in (reverse("eduwisp_portal:vedi_come_esci"), reverse("eduwisp_portal:esci"))
        ):
            return render(request, "eduwisp_portal/sola_lettura.html", status=403)
        return self.get_response(request)
