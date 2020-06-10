from django.shortcuts import render, redirect

# File related libs
from pymongo import MongoClient
import gridfs
import base64
from bson.objectid import ObjectId
from io import BytesIO
from django.http import HttpResponse
from django.http import FileResponse

# Formation and directory libs
import os
import json

# OCR and image processing libs
import cv2
import numpy
from PIL import Image
from pytesseract import *
import pytesseract

# Regex for queries
import re


def homePage(request):
    return render(request, 'archerion/home.html', {})


def getDataBaseConnection(database):
    client = MongoClient()
    db = client[database]
    return db


def selectFileTemplate(request):
    db = getDataBaseConnection('odapas')
    templates = []
    templatesNames = []
    containerNames=[]

    for x in db.documentsTemplates.find():
        template = {}
        template['name'] = x['name']
        templatesNames.append(x['name'])

        if(x['ocrEnable']=="on"):
            byteLikeImage = searchByID(x['previewFileID'])
            binaryString = base64.b64encode(byteLikeImage.getvalue()).decode()

            stringHeader = "data:image/png;base64,"

            template['imageString'] = stringHeader + binaryString
        else: binaryString=""
        templates.append(template)


    for x in db.containers.find():
        containerNames.append(x['name'])

    return render(request, 'archerion/selectTemplate.html',
                  {'containerNames':containerNames,'names': templatesNames, 'templates': json.dumps(templates)})


def showDebugView(request):
    return render(request, 'archerion/debug.html', {})


def createContainerViaAjax(request):
    db= getDataBaseConnection('odapas')
    container={
        "name":request.POST['containerName'],
        "type":request.POST['containerType'],
        "number":request.POST['containerNumber'],
        "outOfMany":request.POST['containerOutOfMany'],
        "shelf":request.POST['containerShelf'],
        "hall":request.POST['containerHall'],
        "docket":request.POST['containerDocket']
    }
    db.containers.insert_one(container)
    newContainersForSelect={}
    containersInDB=[]

    for x in db.containers.find():
        containersInDB.append(x['name'])

    newContainersForSelect[containersInDB[-1]]=containersInDB[-1]
    for x in containersInDB[:len(containersInDB)-1]:
        newContainersForSelect[x]=x


    return HttpResponse(json.dumps(newContainersForSelect),content_type="application/json")

def newFile(request):
    db = getDataBaseConnection('odapas')
    documentName = request.POST['documentName']

    documentTemplate = db.documentsTemplates.find({'name': documentName}).next()
    return render(request, 'archerion/newFile.html',
                  {'container':request.POST['container'],'documentId': documentTemplate['name'],
                   'template': documentTemplate,
                   'fields': documentTemplate['tags'],'ocrEnable':documentTemplate['ocrEnable']})


def searchByID(objectID):
    db = getDataBaseConnection('odapas')
    selectedChunks = db.fs.chunks.find({'files_id': ObjectId(objectID)})
    binaryString = ''
    file = bytearray()
    for x in selectedChunks:
        binaryString += str(base64.b64encode(x['data']), 'utf-8')
        file += x['data']

    fileLike = BytesIO(file)
    return fileLike


def saveFile(request):
    pdf = ""
    address = os.getcwd() + "/temp.pdf"

    os.remove(address) if os.path.isfile(address) else 0

    if request.FILES['fileJPG']:
        imageBytes = request.FILES['fileJPG'].read()
        image = Image.open(BytesIO(imageBytes))
        image.save(address)

        fileID = saveFiletoDB(open(address, "rb").read())

        fileLike = searchByID(fileID)
        os.remove(address)
        return FileResponse(fileLike, 'application/pdf')


# This function can either receive JPG or PDF but in bytes form
def saveFiletoDB(file):
    db = MongoClient().odapas
    fs = gridfs.GridFS(db)
    fileID = fs.put(file)
    return fileID


def sampleFileTest(request):
    file = ""
    fileId = None
    if request.FILES['file']:
        fileId = handleFile(request.FILES['file'])
    else:
        file = "nonData"
    db = getDataBaseConnection('files')

    image = db.fs.chunks.find_one({'files_id': fileId})['data']

    binaryString = base64.b64encode(image)
    stringMetadata = "data:image/png;base64,"

    return render(request, 'archerion/debug.html', {
        'base64StringAlt': stringMetadata + str(binaryString, 'utf-8')})


def saveDocumentTemplate(request):
    fileID = ""
    if len(request.FILES) != 0:
        imageBytes = request.FILES['file'].read()
        fileID = saveFiletoDB(imageBytes)

    document = {
        'name': request.POST['name'],
        'ocrEnable': request.POST.get('ocrEnable','false'),
        'expireEnable': request.POST.get('expireDateEnable','false'),
        'tags': {},
        'previewFileID': fileID,
    }

    tags = {}
    fieldCounter = int(request.POST['fieldCounter'])
    for i in range(fieldCounter):
        index = str(i + 1)
        tagName = request.POST['f' + index]
        tags[tagName] = {}
        tags[tagName]['name'] = tagName
        x = request.POST['x' + index]
        y = request.POST['y' + index]
        width = request.POST['w' + index]
        height = request.POST['h' + index]
        tags[tagName]['coords'] = {
            'x': x,
            'y': y,
            'w': width,
            'h': height
        }

    document['tags'] = tags
    db = getDataBaseConnection('odapas')
    db.documentsTemplates.insert_one(document)
    return redirect('/createDocumentTemplate')


def writeDebugMessage(s):
    with open("debug.txt", "w") as file:
        file.write(s)


def getKeysByOCR(image, documentName):
    img = cv2.imdecode(numpy.fromstring(image.read(), numpy.uint8), cv2.IMREAD_UNCHANGED)
    db = getDataBaseConnection('odapas')
    document = db.documentsTemplates.find_one({"name": documentName})

    fieldsDict = {}
    for tag in document['tags']:
        coords = document['tags'][tag]['coords']

        x, y, w, h = coords['x'], coords['y'], coords['w'], coords['h']

        x, y, w, h = int(float(x)), int(float(y)), int(float(w)), int(float(h))

        partialImg = img[y:y + h, x:x + w]
        # cv2.imwrite(t + ".jpg", partialImg)
        imgForTesseract = Image.fromarray(partialImg)
        extractedField = pytesseract.image_to_string(imgForTesseract)
        fieldsDict[tag] = extractedField
    return fieldsDict


def ajaxExtract(request):
    fieldsDict = getKeysByOCR(request.FILES['fileJPG'], request.POST['documentId'])

    # id=handleFile(request.FILES['fileJPG'])
    return HttpResponse(json.dumps({'fieldsDict': fieldsDict}), content_type="application/json")


def searchView(request):
    # This view have to receive all document types and tags in order to create
    # filters and selective documents
    db = getDataBaseConnection('odapas')
    templates = {}
    for template in db.documentsTemplates.find():
        templateForSelect = {}

        templateForSelect['name'] = template['name']

        tagList = [tag for tag in template['tags']]

        templateForSelect['tags'] = tagList

        templates[template['name']] = templateForSelect

    return render(request, 'archerion/search.html', {"templatesJSON": json.dumps(templates), 'templates': templates})


def executeQuery(request):
    db = getDataBaseConnection('odapas')
    queryResults = {}
    writeDebugMessage(request.POST['templateArray'])
    groupForSearch = []
    for templateName in request.POST['templateArray']:
        for match in db.documentsTemplates.find():
            groupForSearch.append(match)
    writeDebugMessage(groupForSearch[0])

    regx = re.compile(request.POST['key'], re.IGNORECASE)
    return HttpResponse(json.dumps(queryResults), content_type="application/json")


def createDocumentTemplate(request):
    db = getDataBaseConnection('odapas')
    templateNames = ''
    documentFields = ''
    for template in db.documentsTemplates.find():
        if (not template['name'] in templateNames):
            templateNames += template['name'] + ","
        for tag in template['tags']:
            documentFields += tag + ','

    return render(request, 'archerion/newFileTemplate.html', {'names': templateNames, 'fieldNames': documentFields})
