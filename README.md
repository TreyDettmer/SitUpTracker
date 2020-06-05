# SitUpTracker
**Python application that tracks how many sit-ups a person has done**

![Example](misc/SitUpGif.gif)

## Using the Application
### Required Modules
- [Python (I used version 3.6.8)](https://www.python.org/downloads/release/python-368/)
- [opencv-python](https://pypi.org/project/opencv-python/)
- [numpy](https://pypi.org/project/numpy/)
- [Pillow](https://pypi.org/project/Pillow/)
- [playsound](https://pypi.org/project/playsound/)
- [SpeechRecognition](https://pypi.org/project/SpeechRecognition/)
- Internet connection (needed for the speech recognition)

### Required Hardware
- Microphone
- Webcam
### Getting Started
Clone this repository. Using the command prompt, navigate to the repository's directory. Once inside the directory type **python main.py** to run the application.

When the application is ran, you should see your webcam's live feed appear on the screen. If not, check here. On the right hand side of the screen type in how many sit-ups that you plan to do. When finished typing, click the "Done" button. 

Set your webcam view so that you can lay down and do a complete situp with your head and knees in the frame. Make sure that your knees are on the right side of the screen. You can mirror the video by pressing the "Mirror Video" button.

![Correct](misc/SitupCorrectView.JPG) ![Wrong](misc/SitupWrongView.JPG)

Lay down as if you are at the beginning of a sit-up and say "Calibrate". The application should recognize this voice command and create a popup window of the current video frame. Use your cursor to click and create a box around your head. When finished, press the enter key. The application uses this head box to create a pixel to inches scale factor so that the program can estimate the real world measurements of your movements. Next, use your cursor to click and create a box somewhere on or surrounding your head. When finished, press the enter key. Next, use your cursor to click and create a box around your knee. When finished, press the enter key. You should have created three boxes. Here is a GIF to demonstrate.
![Example](misc/SitupTrackerROIdemo.gif)

Now press the Escape key.

Get back into sit-up position and line your head and knee up with the yellow boxes. When you are ready for the application to start tracking your movement, say "Confirm". You should here a sound from the application notifying you that tracking has begun.

### Tracking Errors
Occasionally, the application may lose track of your head or knee location. If you notice this or the right side of the screen turns red (signifying that the tracker has failed), recalibrate the application (i.e. redraw the boxes around your whole head, specific head region, and knee region).

The tracker does best when the object it is tracking is a different color from its surrounding objects, so try not to have a background with colors that could confuse the tracker. Also, don't make any jerky movements as this will likely confuse the tracker, especially with the low framerate of most webcams.

### Reaching Your Sit-up Goal
Once you have reached your sit-up goal, the application will make a chime sound to notify you. You can reset your current sit-up count using the "Reset Count" button. 

### Understanding The Video Graphics
The yellow boxes represent the tracked area calculated by the tracker. The red dots are the centroid of each yellow box. The blue dots are the starting points for the tracked objects. The black ring around the knee box represents the area for which your head must enter in order for the application to register that you have reached the top of a sit-up. 

## Motivation
Whenever I workout, I like to listen to music or watch TV. Sometimes I lose track of how many reps of an exersise I have done. This is what inspired the idea of this application. Certainly, the application wouldn't be that practical, but it would be a fun learning experience. 

## The Development Process
