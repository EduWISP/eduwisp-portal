# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Michele Salerno e i contributori di EduWISP
from django.apps import AppConfig


class PortalConfig(AppConfig):
    name = "eduwisp_portal"
    verbose_name = "interfaccia per ruoli"

    def ready(self):
        from django.contrib.auth.signals import user_logged_out

        from .vista import chiudi_vedi_come

        def all_uscita(sender, request, user, **kwargs):
            if request is not None and user is not None:
                chiudi_vedi_come(request, user, motivo_chiusura="uscita dall'account")

        user_logged_out.connect(all_uscita, dispatch_uid="eduwisp_portal_logout", weak=False)
