from django.urls import path
from . import views

urlpatterns = [
    path('createDocumentTemplate', views.createDocumentTemplate, name='createTemplate'),
    path('saveDocumentTemplate',views.saveDocumentTemplate,name='saveTemplate'),

    path('sendFile',views.sampleFileTest,name='showFileType'),

    path('selectTemplate',views.selectFileTemplate,name='selectTemplate'),

    path('searchForTemplate',views.newFile,name='newFile'),
    path('uploadDocument',views.ajaxExtract, name="ExtractData"),

    path('',views.homePage,name='home'),


    path('saveFile',views.saveFile,name='saveFile'),

    path('search',views.searchView,name='search'),
    path('searchDocuments',views.executeQuery,name='query'),
    path('createContainerViaAjax',views.createContainerViaAjax,name="createContainer"),

]
