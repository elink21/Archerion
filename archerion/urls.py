from django.urls import path
from . import views

urlpatterns = [
    path('createDocumentTemplate', views.createDocumentTemplate, name='createTemplate'),
    path('saveDocumentTemplate',views.saveDocumentTemplate,name='saveTemplate'),

    path('sendFile',views.sampleFileTest,name='showFileType'),
    path('pdf',views.viewFirstPdf,name='pdfDebug'),

    path('selectTemplate',views.selectFileTemplate,name='selectTemplate'),

    path('searchForTemplate',views.newFile,name='newFile'),
    path('uploadDocument',views.ajaxExtract, name="ExtractData"),
]
