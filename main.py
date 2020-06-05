""" SitUpTracker - written by Trey Dettmer

This is my attempt at using object tracking to determine how many situps
a person has done. I would not have been able to complete this project if it
weren't for the great tutorials at https://www.learnopencv.com and https://www.pyimagesearch.com

"""


import cv2;
import tkinter as tk;
import threading;
import time;
import math;
import numpy as np;
from PIL import Image;
from PIL import ImageTk;
from playsound import playsound;
import speech_recognition as sr;



class SitUpTracker:
    """ A class that tracks how many situps a person has done based on a side view video of a person doing situps. """

    def __init__(self,capture):
        """ Initialize SitUpTracker. """
        #create window
        self.root = tk.Tk()
        self.canvas = tk.Canvas(self.root, height=self.root.winfo_screenheight(), width=self.root.winfo_screenwidth());
        self.canvas.pack();

        #create video frame and widgets
        self.videoFrame = tk.Frame(self.root, bg="#bed5e8");
        self.videoFrame.place(relx=0, rely=0, relwidth=0.7, relheight=1);
        self.calibrateButton = tk.Button(self.videoFrame,text="Calibrate",command=self.defineBboxes);
        self.calibrateButton.place(relx=0,rely=.8,relwidth=.5,relheight=.1);
        self.confirmCalibrationButton = tk.Button(self.videoFrame,text="Confirm",state="disabled",command=self.confirmCalibration);
        self.confirmCalibrationButton.place(relx=.5,rely=.8,relwidth=.5,relheight=.1);

        #create info frame (right side of screen) and widgets
        self.infoFrame = tk.Frame(self.root,bg="white")
        self.infoFrame.place(relx=.7,rely=0,relwidth=0.3,relheight=1)
        self.guiSitUpCounterText = tk.Label(self.infoFrame,text="SitUp Count",font=("Helvetica", 18),bg = self.infoFrame["bg"])
        self.guiSitUpCounterText.place(relx= 0.5,rely=.09,anchor="center");
        self.guiSitUpCounterCount = tk.Label(self.infoFrame,text="0/2",font=("Helvetica", 20),bg = self.infoFrame["bg"])
        self.guiSitUpCounterCount.place(relx = 0.5,rely=.15,anchor="center")
        self.guiSitUpGoalLabel = tk.Label(self.infoFrame,text="Set SitUp Goal:",font=("Helvetica", 16),bg = self.infoFrame["bg"])
        self.guiSitUpGoalLabel.place(relx=.06,rely=.3);
        self.strSitUpGoal = tk.StringVar();
        self.strSitUpGoal.set("2")
        self.guiSitUpGoalEntry = tk.Entry(self.infoFrame,textvariable=self.strSitUpGoal,font=("Helvetica", 14))
        self.guiSitUpGoalEntry.place(relx=.46,rely=.3,relwidth=.1)
        self.confirmEntryButton = tk.Button(self.infoFrame,text="Done",command=self.setSitUpGoal,font=("Helvetica", 14))
        self.confirmEntryButton.place(relx=.6,rely=.29)
        self.mirrorVideoButton = tk.Button(self.infoFrame,text="Mirror Video",font=("Helvetica", 14),command=self.mirrorVideoButtonCallback);
        self.mirrorVideoButton.place(relx=.5,rely=.5,anchor="center")
        self.resetSitUpCountButton = tk.Button(self.infoFrame,text="Reset Count",font=("Helvetica", 14),command=self.resetSitUpCountButtonCallback)
        self.resetSitUpCountButton.place(relx=.5,rely=.6,anchor="center")

        #video capture object
        self.capture = capture;
        #the current video frame
        self.frame = None;
        #copy of current video frame without anything drawn on it
        self.frameOg = None;


        self.mirrorVideo = False;
        #panel that the video is displayed on
        self.videoFramePanel = None;
        #the boxes (Regions of Interest) that are created to initialize tracking
        self.bboxes = []
        #the amount of padding to add to the area that is still visible the object tracker once the mask is applied
        self.maskBufferSize = 50;
        #the object tracker
        self.multiTracker = None
        #deteremines whether the tracker should be attempting to track whatever is in self.bboxes
        self.waitForCalibrationConfirmation = False;
        #threading event which is called when the user exits the program
        self.stopEvent = threading.Event();
        #whether the user can say confirm (based on time since last "confirm")
        self.canSayConfirm = True;
        #whether the user can say calibrate (based on time since last "calibrate")
        self.canSayCalibrate = True;
        #whether the user just said "confirm"
        self.voiceCalledConfirm = False;
        #whether the user just said "calibrate"
        self.voiceCalledCalibrate = False;
        #whether the user reached the goal number of situps
        self.reachedGoal = False;
        #Thread that plays the video
        self.videoThread = None;
        self.videoThread = threading.Thread(target=self.videoLoop,args=(),daemon=True);
        self.videoThread.start();
        #thread that listens for the user's voice commands
        self.voiceThread = threading.Thread(target=self.voiceLoop,args=(),daemon=True);
        self.voiceThread.start();

        #the current situp count
        self.currentSitUpCount = 0;
        #the situp goal
        self.sitUpGoal = 2;

        #initial distance from the user's head to the user's knee
        self.initialHeadKneeDistance = 0;
        #initial position of the user's head
        self.initialHeadPosition = (0,0);
        #initial position of the user's knee
        self.initialKneePosition = (0,0);

        #whether the user has reached the top of the current situp
        self.reachedTop = False;
        #height in pixels of the user's head
        self.headHeight = 0.0;
        #title of the window
        self.root.wm_title("SitUpTracker");
        #what to do when the window is closed
        self.root.wm_protocol("WM_DELETE_WINDOW",self.onClose)



    def resetSitUpCountButtonCallback(self):
        """ Reset the situp count."""
        self.currentSitUpCount = 0;
        self.reachedGoal = False;
        self.reachedTop = False;
        self.guiSitUpCounterCount["text"] = str(self.currentSitUpCount) + "/" + str(self.sitUpGoal)

    def mirrorVideoButtonCallback(self):
        """ Mirror the video"""
        self.mirrorVideo = not self.mirrorVideo;

    def voiceLoop(self):
        """ Listen to user's voice command """
        while not self.stopEvent.is_set():

            r = sr.Recognizer()

            with sr.Microphone() as source:
                audio = r.listen(source)


            try:

                speech = r.recognize_google(audio)
                if "confirm" in speech:
                    if self.canSayConfirm and not self.voiceCalledConfirm:
                        self.canSayConfirm = False;
                        self.voiceCalledConfirm = True;
                        t = threading.Timer(5.0, self.confirmTimerCallback);
                        t.start();
                    else:
                        print("You said confirm before cooldown finished")


                elif "calibrate" in speech:
                    if self.canSayCalibrate and not self.voiceCalledCalibrate:
                        self.canSayCalibrate = False;
                        self.voiceCalledCalibrate = True;
                        t = threading.Timer(5.0,self.calibrateTimerCallback);
                        t.start();
                    else:
                        print("You said calibrate before cooldown finished")
            except Exception as e:
                pass


    def defineBboxes(self):
        """ Define the regions of interest. (Head size, head tracking point, knee tracking point)"""

        if self.frame is not None:
            playsound("sounds/click_sound.mp3");

            self.frame = cv2.resize(self.frame, (960, 540));
            if self.mirrorVideo:
                self.frame = cv2.flip(self.frame,1);
            bboxes = cv2.selectROIs("Select Keypoints", self.frameOg, True, False);

            if len(bboxes) != 3:
                self.multiTracker = None
                self.bboxes = []
                self.waitForCalibrationConfirmation = False;
                cv2.destroyWindow("Select Keypoints");
                self.resolveError();
                return
            temp = [];
            for i in range(len(bboxes)):
                box = (bboxes[i][0], bboxes[i][1], bboxes[i][2], bboxes[i][3]);
                temp.append(box);

            self.multiTracker = cv2.MultiTracker_create();
            self.waitForCalibrationConfirmation = True;
            #the first box is for determining the head height so don't track it
            if len(temp) > 2:
                headBox = temp.pop(0);
                self.headHeight = np.maximum(headBox[3], headBox[2])
            self.bboxes = temp;
            for bbox in self.bboxes:
                self.multiTracker.add(cv2.TrackerCSRT_create(), self.frame, bbox);
            if len(self.bboxes) > 1:
                headCenter = self.calcuateCenterOfRect(self.bboxes[0]);
                self.initialHeadPosition = headCenter;
                kneeCenter = self.calcuateCenterOfRect(self.bboxes[1])
                self.initialKneePosition = kneeCenter;
                self.initialHeadKneeDistance = self.calculateDistanceBetweenPoints(headCenter, kneeCenter)
            self.confirmCalibrationButton["state"] = "normal";
            cv2.destroyWindow("Select Keypoints");
            self.resolveError();


    def confirmCalibration(self):
        """ Start tracking the user's head and knee. """
        playsound("sounds/click2_sound.mp3");
        self.waitForCalibrationConfirmation = not self.waitForCalibrationConfirmation;
        self.calibrationSitUp = True;



    def setSitUpGoal(self):
        """ Set the situp goal based on what the user typed into the entry box. """
        try:
            situpGoal = int(self.guiSitUpGoalEntry.get());
            if situpGoal <= self.currentSitUpCount:

                self.sitUpGoal = self.currentSitUpCount + 1
            else:
                self.sitUpGoal = int(self.guiSitUpGoalEntry.get());
        except ValueError as e:
            self.sitUpGoal = self.currentSitUpCount + 1;
        self.guiSitUpCounterCount["text"] = str(self.currentSitUpCount) + "/" + str(self.sitUpGoal)
        return True



    def confirmTimerCallback(self):
        """ Allow the user to say confirm. """
        self.canSayConfirm = True;

    def calibrateTimerCallback(self):
        """ Allow the user to say calibrate. """
        self.canSayCalibrate = True;

    def soundFinishedAlarm(self):
        """ The user reached the goal so stop tracking and play a happy sound. """
        self.reachedGoal = True;
        playsound("sounds/bell_chime_alert.mp3")


    def calculateSitUp(self):
        """ Calculate whether the user did a situp. """
        if not self.reachedGoal:
            if self.multiTracker is not None:
                if len(self.bboxes) >= 2:

                    headCenter = self.calcuateCenterOfRect(self.bboxes[0]);
                    kneeCenter = self.calcuateCenterOfRect(self.bboxes[1])
                    distance = self.calculateDistanceBetweenPoints(headCenter,kneeCenter)
                    headToHeadDistance = self.calculateDistanceBetweenPoints(headCenter,self.initialHeadPosition)

                    if headToHeadDistance < 6: #at the bottom of situp

                        if self.reachedTop:

                            self.currentSitUpCount += 1;

                            self.guiSitUpCounterCount["text"] = str(self.currentSitUpCount) + "/" + str(self.sitUpGoal)
                            if self.currentSitUpCount == self.sitUpGoal:
                                self.soundFinishedAlarm();
                            self.reachedTop = False;


                    elif distance <= .4*self.initialHeadKneeDistance: #at the top of situp

                        self.reachedTop = True;






    def flashError(self):
        """ Make the info frame background red to signify that something went wrong. """
        self.infoFrame["bg"] = "red";

    def resolveError(self):
        """ Make the info frame background white since nothing is wrong. """
        self.infoFrame["bg"] = "white";


    def calcuateCenterOfRect(self,rect):
        """ Calculate and return the center of a given rect. """
        p1 = (int(rect[0]), int(rect[1]))
        p2 = (int(rect[0] + rect[2]), int(rect[1] + rect[3]))
        return (int((p1[0] + p2[0]) / 2), int((p1[1] + p2[1]) / 2))

    def calculateDistanceBetweenPoints(self,p1,p2):
        """ Calculate and return the estimated distance in inches between two given points"""

        pixelDistance = math.sqrt(math.pow((p2[0] - p1[0]),2) + math.pow((p2[1] - p1[1]),2));
        if len(self.bboxes) > 1:

            actualHeadSize = 9.4 #average head height in inches
            pixel_per_inch = self.headHeight / actualHeadSize
            return pixelDistance/pixel_per_inch
        return None

    def calculatePixelDistanceFromActual(self,actualDistance):
        """ Return the actual distance given a pixel distance. """

        actualHeadSize = 9.4 #average head height in inches
        pixel_per_inch = self.headHeight / actualHeadSize
        return actualDistance*pixel_per_inch;

    def videoLoop(self):
        """ Play the video. """

        try:
            while not self.stopEvent.is_set():
                if self.voiceCalledCalibrate:
                    self.defineBboxes();
                    self.voiceCalledCalibrate = False;
                if self.voiceCalledConfirm:
                    self.confirmCalibration();
                    self.voiceCalledConfirm = False;

                hasFrame, self.frame = self.capture.read();

                if self.frame is not None:
                    self.frame = cv2.resize(self.frame, (960, 540));
                    if self.mirrorVideo:
                        self.frame = cv2.flip(self.frame,1);
                    self.frameOg = self.frame.copy();

                    if not self.reachedGoal:

                        if len(self.bboxes) >= 2:
                            """ Create a mask over the frame so that the tracker is less likely to lose track of the user's head and knee. """
                            if self.initialHeadPosition[1] + self.maskBufferSize < self.frame.shape[0] and self.initialHeadPosition[0] - self.maskBufferSize >= 0 and self.initialKneePosition[0] + self.maskBufferSize < self.frame.shape[1]:
                                points = np.array([
                                    [self.initialHeadPosition[0] - self.maskBufferSize, self.initialHeadPosition[1] + self.maskBufferSize],
                                    [self.initialKneePosition[0] + self.maskBufferSize, self.initialKneePosition[1]],
                                    [self.initialKneePosition[0] + self.maskBufferSize, 0],
                                    [self.initialHeadPosition[0]-self.maskBufferSize, 0],
                                    [self.initialHeadPosition[0]-self.maskBufferSize, self.initialHeadPosition[1]+self.maskBufferSize]
                                ], np.int32)
                            else:

                                points = np.array([
                                    [self.initialHeadPosition[0],self.initialHeadPosition[1]],
                                    [self.initialKneePosition[0],self.initialKneePosition[1]],
                                    [self.initialKneePosition[0],0],
                                    [self.initialHeadPosition[0],0],
                                    [self.initialHeadPosition[0], self.initialHeadPosition[1]]
                                ], np.int32)
                            rect = cv2.boundingRect(points)
                            x, y, w, h = rect

                            maskedFrame = self.frame.copy();
                            cropped = maskedFrame[y:y + h, x:x + w]
                            points = points - points.min(axis=0);
                            mask = np.zeros((cropped.shape[0],cropped.shape[1]),np.uint8)
                            cv2.drawContours(mask, [points], -1, (255, 255, 255), -1, cv2.LINE_AA)
                            maskedFrame[y:y + h, x:x + w] = cv2.bitwise_and(maskedFrame[y:y + h, x:x + w],maskedFrame[y:y + h, x:x + w],mask=mask)
                            maskedFrame[:,:x] = [0,0,0]
                            maskedFrame[:,x+w:] = [0,0,0]
                            maskedFrame[y+h:,:] = [0,0,0]

                            if self.multiTracker is not None:
                                if not self.waitForCalibrationConfirmation:
                                    success, boxes = self.multiTracker.update(maskedFrame);

                                    if not success: #tracker failed so have the user draw the bboxes again

                                        self.multiTracker = None;
                                        self.bboxes = [];
                                        print("Tracker failed.")
                                        self.flashError()
                                        self.defineBboxes()
                                    else:

                                        self.bboxes = boxes;
                                        self.calculateSitUp();
                                        cv2.circle(self.frame,self.initialHeadPosition,3,(255,0,0),-1)
                                        cv2.circle(self.frame,self.initialKneePosition,3,(255,0,0),-1)

                                        for i, box in enumerate(boxes):

                                            p1 = (int(box[0]), int(box[1]))
                                            p2 = (int(box[0] + box[2]), int(box[1] + box[3]))

                                            if i == 0:

                                                cv2.rectangle(self.frame, p1, p2, (0, 255, 255), 2, 1)
                                                cv2.circle(self.frame,
                                                           (int((p1[0] + p2[0]) / 2), int((p1[1] + p2[1]) / 2)), 5,
                                                           (0, 0, 255), -1);
                                                cv2.putText(self.frame, "Head", (int(box[0]), int(box[1] - 2)),
                                                            cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                                                            (0, 255, 255), 1);
                                            elif i == 1:
                                                cv2.rectangle(self.frame, p1, p2, (0, 255, 255), 2, 1)
                                                cv2.circle(self.frame,
                                                           (int((p1[0] + p2[0]) / 2), int((p1[1] + p2[1]) / 2)), 5,
                                                           (0, 0, 255), -1);
                                                cv2.circle(self.frame,(int((p1[0] + p2[0])/2),int((p1[1] + p2[1])/2)),int(self.calculatePixelDistanceFromActual(self.initialHeadKneeDistance*.4)),(0,0,0),2)
                                                cv2.putText(self.frame, "Knee", (int(box[0]), int(box[1] - 2)),
                                                            cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                                                            (0, 255, 255), 1);

                                else:
                                    for i, box in enumerate(self.bboxes):
                                        p1 = (int(box[0]), int(box[1]))
                                        p2 = (int(box[0] + box[2]), int(box[1] + box[3]))
                                        cv2.rectangle(self.frame, p1, p2, (0, 255, 255), 2, 1)
                                        if i == 0:
                                            cv2.putText(self.frame, "Head", (int(box[0]), int(box[1] - 2)),
                                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                                                        (0, 255, 255), 1)
                                        elif i == 1:
                                            cv2.putText(self.frame, "Knee", (int(box[0]), int(box[1] - 2)),
                                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                                                        (0, 255, 255), 1)






                    #convert the video frame to rgb color
                    image = cv2.cvtColor(self.frame,cv2.COLOR_BGR2RGB);
                    #update the displayed video frame
                    image = Image.fromarray(image);
                    image = ImageTk.PhotoImage(image);
                    if self.videoFramePanel is None:
                        self.videoFramePanel = tk.Label(self.videoFrame,image=image);
                        self.videoFramePanel.image = image;
                        self.videoFramePanel.pack();
                    else:
                        self.videoFramePanel.configure(image=image);
                        self.videoFramePanel.image = image;



                else:
                    print("frame is none")
                    break;


        except Exception as e:
            print("fail: " + str(e))


    def onClose(self):
        """ Destroy the video feed and the window. """
        self.capture.release();
        self.root.quit();
        print("Destroyed")




if __name__ == "__main__":
    cap = cv2.VideoCapture(0);
    #give time for the webcam to warm up
    time.sleep(1.0);
    sitUpTracker = SitUpTracker(cap);
    sitUpTracker.root.mainloop();