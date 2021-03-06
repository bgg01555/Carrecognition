#!/usr/bin/env python
import cv2 as cv
import os
import sys
import numpy as np
from Module.object_tracker import Tracker
from Module.color_detection import process_image
from keras_applications.vgg16 import VGG16
from keras import models, layers
from keras import optimizers
import keras
import datetime
from datetime import timedelta

from recognition.models import Cctv, CctvLog
from car.models import Car

def printDebug(a,b):
    if a == True:
        print(b)

def CarClassifier(npimg, model, car_label_strlist):
    try:
        npimg = npimg.astype('float32')/255.0
        #pred = model.predict(npimg)
        output_label = model.predict_classes(npimg)
        #print(output_label)
        labelstr = car_label_strlist[int(output_label[0])][1]
        label_com = car_label_strlist[int(output_label[0])][1]
        return labelstr
    except:
        print("error")

def imread(filename, flags=cv.IMREAD_COLOR, dtype=np.uint8): # code snippet for read utf-8
    try:
        n = np.fromfile(filename, dtype)
        img = cv.imdecode(n, flags)
        return img
    except Exception as e:
        print(e)
        return None

def imwrite(filename, img, params=None): # code snippet for read utf-8
    try:
        ext = os.path.splitext(filename)[1]
        result, n = cv.imencode(ext, img, params)
        if result:
            with open(filename, mode='w+b') as f:
                n.tofile(f)
            return True
        else:
            return False
    except Exception as e:
        print(e)
        return False

# if __name__ =="__main__":
def Wls(video, start_time, location, latitude, longtitude):
    """"""
    savePath = video
    video = 'static/videos/'+video
    uploaded_time = 0.0

    baseline_01 = 0.55
    baseline_02 = 1.0
    writer = None
    frame_per_second = 30
    maxLost = 3  # maximum number of object losts counted when the object is being tracked

    car_label_strlist = np.loadtxt("Module/car_label2.csv", delimiter=',', dtype='str')

    #load vgg16
    pre_model = VGG16(weights='imagenet', include_top=False, input_shape=(224, 224, 3), backend=keras.backend,
                      layers=keras.layers, models=keras.models, utils=keras.utils)
    pre_model.trainable = True
    pre_model.summary()

    # add output layer for VGG16 output (4096 -> 1000 => 4096 -> 1000 -> 100)
    vgg_model = models.Sequential()
    vgg_model.add(pre_model)
    vgg_model.add(layers.Flatten())
    vgg_model.add(layers.Dense(4096, activation='relu'))
    vgg_model.add(layers.Dense(1024, activation='relu'))
    vgg_model.add(layers.Dense(20, activation='softmax'))  # practical

    vgg_model.summary()
    vgg_model.compile(loss='categorical_crossentropy', optimizer=optimizers.RMSprop(lr=2e-5), metrics=['acc'])
    #vgg_model.load_weights("y_s_weights.h5") # ????????? ?????? 1
    #vgg_model.load_weights("y_up_weights.h5") # ????????? ?????? 2
    vgg_model.load_weights("Module/CarDatabaseShare/y_seventh_car_weight.hdf5") #????????? ?????? 3
    # Load Yolo
    net = cv.dnn.readNet("Module/CarDatabaseShare/yolov3.weights", "Module/CarDatabaseShare/yolov3.cfg")
    classes = []
    with open("Module/CarDatabaseShare/coco.names", "r") as f:
        classes = [line.strip() for line in f.readlines()]
    layer_names = net.getLayerNames()
    output_layers = [layer_names[i[0] - 1] for i in net.getUnconnectedOutLayers()]

    #print(len(classes))
    colors = np.random.uniform(0, 255, size=(len(classes), 3))
    #print(colors)

    bbox_colors = np.random.randint(0, 255, size=(len(classes), 3))
    #print(bbox_colors)

    tracker = Tracker(maxLost=maxLost)
    cap = cv.VideoCapture(video)

    # Check if camera opened successfully
    if not cap.isOpened():
        print("Error opening video stream or file")
        sys.exit()

    vwidth = cap.get(3)  # float
    vheight = cap.get(4)  # float
    frame_count = 0
    while True:
        _, frame = cap.read()

        if _ is not True:
            break

        height, width, channels = frame.shape

        # Detecting objects
        blob = cv.dnn.blobFromImage(frame, 0.00392, (320, 320), (0, 0, 0), True, crop=False)

        net.setInput(blob)
        outs = net.forward(output_layers)

        # Showing informations on the screen
        class_ids = []
        confidences = []
        boxes = []
        detected_boxes = []
        detected_label = []
        detected_times = []
        detected_colors = []

        for out in outs:
            for detection in out:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                if confidence > 0.5:
                    # Object detected
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)

                    # Rectangle coordinates
                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)

                    boxes.append([x, y, w, h])
                    confidences.append(float(confidence))
                    class_ids.append(class_id)

        indexes = cv.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)
        # print(indexes)
        font = cv.FONT_HERSHEY_PLAIN

        for i in range(len(boxes)):
            if i in indexes:
                x, y, w, h = boxes[i]
                if h > 40 and w > 50 and class_ids[i] == 2 and y > (vheight * baseline_01) and (y + h) < (vheight * baseline_02):
                    cropimg = frame.copy()
                    cropimg = frame[y:y+h, x:x+w]
                    try:
                        colorlabel = process_image(cropimg)
                        cropimg = cv.cvtColor(cropimg, cv.COLOR_BGR2GRAY)
                        cropimg = cv.resize(cropimg, dsize=(224, 224), interpolation=cv.INTER_AREA)
                        cropimg = cv.GaussianBlur(cropimg, (3, 3), 0)
                        cannimg = cv.Canny(cropimg, 25, 50)
                        npimg = np.asarray(cannimg)
                        npimg = np.stack((cannimg,)*3, axis=-1)
                        npimg = np.expand_dims(npimg, axis=0)
                        #print(npimg.shape)
                        car_recog = CarClassifier(npimg, vgg_model, car_label_strlist)
                        detected_boxes.append((x, y, x + w, y + h))
                        detected_label.append(car_recog)
                        detected_times.append(int(frame_count/frame_per_second) + 1)
                        detected_colors.append(colorlabel)
                    except:
                        continue
                    color = colors[i]
                    cv.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                    #cv.putText(frame, car_recog, (x, y + 30), font, 2, color, 3)
                    #cv.putText(frame, label, (x, y + 20), font, 3, color, 3)
                elif (class_ids[i] == 3 or class_ids[i] == 5 or class_ids[i] == 7) and y > (vheight * baseline_01) and (y + h) < (vheight * baseline_02):
                    cropimg = frame.copy()
                    cropimg = frame[y:y+h, x:x+w]
                    colorlabel = process_image(cropimg)
                    label = str(classes[class_ids[i]])
                    color = colors[i]
                    cv.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                    #cv.putText(frame, label, (x, y + 20), font, 2, color, 3)
                    detected_boxes.append((x, y, x + w, y + h))
                    detected_label.append(label)
                    detected_times.append(int(frame_count/frame_per_second) + 1)
                    detected_colors.append(colorlabel)

        cv.line(frame, (0,int(vheight*baseline_01)), (int(vwidth-1), int(vheight*baseline_01)), (0,0,0), 2)
        cv.line(frame, (0, int(vheight * baseline_02)), (int(vwidth - 1), int(vheight * baseline_02)), (0, 0, 0), 2)
        objects = tracker.update(detected_boxes, detected_label, detected_times, detected_colors)  # update tracker based on the newly detected objects

        for (objectID, centroid) in objects.items():
            text = "ID {}".format(objectID)
            if centroid[1] > (vheight * baseline_01) and centroid[1] < (vheight * baseline_02):
                cv.putText(frame, text, (centroid[0] - 10, centroid[1] - 10), cv.FONT_HERSHEY_SIMPLEX,
                           0.5, (0, 255, 0), 2)
                cv.circle(frame, (centroid[0], centroid[1]), 4, (0, 255, 0), -1)

        # cv.imshow('', frame)
        key = cv.waitKey(1)
        if key == 27:
            break
        if writer is None:
            startTime = start_time.replace(" ", "-")
            startTime = startTime.replace(":", "-")
            savepath=savePath.split(".")[0]
            filePath= "static/output/" + savepath + "-"  + startTime + ".mp4"
            print(filePath)
            fourcc = cv.VideoWriter_fourcc(*"h264")
            # fourcc = cv.VideoWriter_fourcc(*"mp4v")
            writer = cv.VideoWriter(filePath, fourcc, 30, (int(vwidth), int(vheight)), True)
        writer.write(frame)
        if frame_count % 50 == 0:
            classified_info_list = tracker.getClassifiedInfo()
            for obj in classified_info_list:
                print(obj)

        frame_count+=1


    cctv = Cctv(video_link=filePath, location=location, start_time=start_time, latitude=latitude, longtitude=longtitude)
    cctv.save()

    classified_info_list = tracker.getClassifiedInfo()
    for obj in classified_info_list:
        print(obj)

#car model ?????? ???????????????, appearance_time ????????? ??? ?????????, ????????? ????????? ??????
#CCTV video_link ????????? ?????? // ??????
    for obj in classified_info_list:
        try:
            model_brand = obj[1][0][0].split("-")
            model = model_brand[0]
            brand = model_brand[1]
        except:
            model = obj[1][0][0]
            brand = obj[1][0][0]
        try:
            car = Car.objects.get(model=model)
            # car = Car.objects.get(model='a')
        except:
            car = Car(model=model, brand=brand)
            # car = Car(model='a', brand="")
            car.save()

        start_time = datetime.datetime.strptime(str(start_time), '%Y-%m-%d %H:%M:%S')
        appearance_time = start_time + timedelta(seconds=obj[2])

        cctv_log = CctvLog(car_model=car, color=obj[3], appearance_time=appearance_time, cctv_id=cctv)
        cctv_log.save()

    writer.release()
    cap.release()
    os.remove(video)
    cv.destroyAllWindows()
