# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Michele Salerno e i contributori di EduWISP
from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "eduwisp_portal"

urlpatterns = [
    path("", views.home, name="home"),
    path(
        "accedi/",
        auth_views.LoginView.as_view(template_name="eduwisp_portal/accedi.html"),
        name="accedi",
    ),
    path("esci/", auth_views.LogoutView.as_view(next_page="eduwisp_portal:accedi"), name="esci"),
    path("ruolo/", views.scegli_ruolo, name="ruolo"),
    path("amministrazione/", views.amministrazione, name="amministrazione"),
    path("vedi-come/", views.vedi_come, name="vedi_come"),
    path("vedi-come/esci/", views.vedi_come_esci, name="vedi_come_esci"),
    path("preside/", views.preside, name="preside"),
    path("docente/", views.docente, name="docente"),
    path("classe/<int:pk>/", views.classe, name="classe"),
    path("classe/<int:pk>/sblocca/", views.sblocca_app, name="sblocca_app"),
    path("sblocco/<int:pk>/termina/", views.termina_sblocco, name="termina_sblocco"),
    path("famiglia/", views.famiglia, name="famiglia"),
    path("richieste/", views.richieste, name="richieste"),
    path("richieste/<int:pk>/", views.richiesta, name="richiesta"),
]
