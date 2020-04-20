from django.shortcuts import render, redirect

#File related libs
from pymongo import MongoClient
import gridfs
import base64
from bson.objectid import ObjectId
from io import BytesIO
from django.http import HttpResponse
from django.http import FileResponse

#Formation and directory libs
import os
import json

#OCR and image processing libs
import cv2
import numpy
from PIL import Image
from pytesseract import *
import pytesseract



def getDataBaseConnection(database):
    client=MongoClient()
    db=client[database]
    return db


def getImageById(imageId):
    client = MongoClient()
    db = client.odapas


def selectFileTemplate(request):
    db= getDataBaseConnection('odapas')
    documentsNames = []
    for x in db.documentsTemplates.find():
        documentsNames.append(x['name'])
    return render(request, 'archerion/selectTemplate.html', {'names': documentsNames})


def showDebugView(request):
    return render(request, 'archerion/debug.html', {})


def newFile(request):
    db= getDataBaseConnection('odapas')
    documentName = request.POST['documentName']
    documentTemplate = db.documentsTemplates.find({'name': documentName}).next()
    return render(request, 'archerion/newFile.html', {'documentId': documentTemplate['name'], 'template': documentTemplate,
                                                'fields': documentTemplate['tags']})


#Todo: change all this function into a useful onee
def viewFirstPdf(request):
    db= getDataBaseConnection('gridf_example')
    selectedChunks = db.fs.chunks.find({'files_id': ObjectId('5e6fdca7c1a5e69a764f1451')})
    binaryString = ''
    file = bytearray()
    for x in selectedChunks:
        binaryString += str(base64.b64encode(x['data']), 'utf-8')
        file += x['data']

    fileLike = BytesIO(file)
    # return render(request,'archerion/debug.html',{'dataA':binaryString,'dataB':x})
    return FileResponse(fileLike, content_type='application/pdf')



def handleFile(file):
    db = MongoClient().gridf_example
    fs = gridfs.GridFS(db)

    fileId = fs.put(file)

    with open(path + '/temp.png', 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)
    return fileId


def sampleFileTest(request):
    file = ""
    fileId = None
    if request.FILES['file']:
        fileId = handleFile(request.FILES['file'])
    else:
        file = "nonData"
    db= getDataBaseConnection('gridf_example')

    image = db.fs.chunks.find_one({'files_id': fileId})['data']

    binaryString = base64.b64encode(image)
    stringMetadata = "data:image/png;base64,"

    return render(request, 'archerion/debug.html', {
        'base64StringAlt': stringMetadata + str(binaryString, 'utf-8')})


def saveDocumentTemplate(request):
    document = {
        'name': request.POST['name'],
        'ocrEnable': request.POST['ocrEnable'],
        'tags': {},
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
    db= getDataBaseConnection('odapas')
    db.documentsTemplates.insert_one(document)
    return redirect('/createDocumentTemplate')


def writeDebugMessage(s):
    with open("debug.txt", "w") as file:
        file.write(s)


def getKeysByOCR(image, documentName):
    img = cv2.imdecode(numpy.fromstring(image.read(), numpy.uint8), cv2.IMREAD_UNCHANGED)
    db= getDataBaseConnection('odapas')
    document = db.documentsTemplates.find_one({"name": documentName})

    fieldsDict = {}
    for tag in document['tags']:
        coords = document['tags'][tag]['coords']

        x, y, w, h = coords['x'], coords['y'], coords['w'], coords['h']

        x, y, w, h = int(float(x)), int(float(y)), int(float(w)), int(float(h))

        partialImg = img[y:y + h, x:x + w]
        #cv2.imwrite(t + ".jpg", partialImg)
        imgForTesseract = Image.fromarray(partialImg)
        extractedField = pytesseract.image_to_string(imgForTesseract)
        fieldsDict[tag] = extractedField
    return fieldsDict


def ajaxExtract(request):

    fieldsDict = getKeysByOCR(request.FILES['fileJPG'], request.POST['documentId'])

    # id=handleFile(request.FILES['fileJPG'])
    return HttpResponse(json.dumps({'fieldsDict':fieldsDict}), content_type="application/json")



def createDocumentTemplate(request):
    db= getDataBaseConnection('odapas')
    templateNames = ''
    documentFields = ''
    for template in db.documentsTemplates.find():
        if (not template['name'] in templateNames):
            templateNames += template['name'] + ","
        for tag in template['tags']:
            documentFields += tag + ','

    return render(request, 'archerion/newFileTemplate.html', {'names': templateNames, 'fieldNames': documentFields})
