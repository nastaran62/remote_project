'''
Steps:
0- Run the scenario
1- Wait for video conferencing
2- Share the screen
3- Open monitoring in another browser
'''

import os
import logging
logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=logging.DEBUG)
import time
import datetime
import http.client
import pickle
from windows import ImageWindow, MessageButtonWindow, TimerWindow
from prepare_stimuli import prepare_stimuli_list
import time
import argparse
from screeninfo import get_monitors
import gi
from gi.repository import Gtk, GdkPixbuf, GLib, Gdk
gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')

import csv

EMOTIONS = {"1": "High-Valence, High-Arousal",
            "2": "High-Valence, Low-Arousal",
            "3": "Low-Valence, High-Arousal",
            "4": "Low-Valence, Low-Arousal"}

def read_stimuli_order(subject_id):
    stimuli_order_file_path = "stimuli/remote/p{}_stimuli.csv".format(str(subject_id).zfill(2))
    print(stimuli_order_file_path)
    if not os.path.exists(stimuli_order_file_path):
        prepare_stimuli_list(subject_id)
    order = []
    with open(stimuli_order_file_path, "r") as csv_file:
        reader = csv.reader(csv_file)
        for row in reader:
            order.append(row[0])
    print(order)
    return order

STIMULI_PATH = "stimuli/all_images/"

class BackgroudWindow(Gtk.Window):
    def __init__(self, experiment_id, subject_id, host):
        self._host = host
        self._http_client = http.client.HTTPConnection(self._host, timeout=3)
        os.makedirs("logs", exist_ok=True)
        time_str = datetime.datetime.strftime(datetime.datetime.now(),
                                              "%Y-%m-%dT%H-%M-%S")
        logging.basicConfig(filename='logs/exp2_f2f_log_{0}_{1}.log'.format(experiment_id, time_str),
                            level=logging.DEBUG)
        self._experiment_id = experiment_id

        self._stimuli_list = read_stimuli_order(subject_id)

        self._index = 0
        logging.info("Emotion order is {}".format(self._stimuli_list))

        Gtk.Window.__init__(self, title="")
        image_box = Gtk.Box()
        monitors = get_monitors()       
        image_width = monitors[0].width
        image_height = monitors[0].height
        print(image_width, image_height)
        background_path = "images/gray_image.jpg"
        pixbuf = \
            GdkPixbuf.Pixbuf.new_from_file_at_scale(background_path,
                                                    image_width,
                                                    image_height, False)
        image = Gtk.Image()
        image.set_from_pixbuf(pixbuf)
        image_box.pack_start(image, False, False, 0)
        self.add(image_box)

        self.image_window = ImageWindow("image_window", monitor_no=1)
        self.image_window.set_image(background_path)


    def show(self, *args):
        '''
        Shows the background window (A gray image)
        '''
        self.connect("destroy", Gtk.main_quit)
        self.fullscreen()
        self.show_all()
        self.image_window.show_window()

        GLib.timeout_add_seconds(5, self._show_message)
        GLib.timeout_add_seconds(1, self._move_image_window)
        Gtk.main()

    def _move_image_window(self, *args):
        os.system("wmctrl -ir $(wmctrl -l |grep image_window |grep -v grep |cut -d ' ' -f1) -e 0,1200,0,-1,-1")

    def _show_message(self, *args, message="Start"):
        '''
        Showing a message before each stimuli
        '''

        logging.info("Start time {0}".format(datetime.datetime.now()))
        message = \
            MessageButtonWindow("Info", message)
        message.show()

        if self._index >= 8:
            message.connect("destroy", self._done)
        else:
            message.connect("destroy", self._show_fixation_cross)

    def _show_fixation_cross(self, *args):
        '''
        Showing fixation cross before each stimuli
        '''
        logging.info("Fixation cross {0}".format(datetime.datetime.now()))
        self.image_window.set_image("images/fixation_cross.jpg")

        logging.info(f"Sending START. Stimulus: {self._stimuli_list[self._index][:-4]}")
        self.__post_trigger({
            'type': 'START',
            'experiment_id': self._experiment_id,
            'stimulus_id': self._stimuli_list[self._index][:-4]})

        GLib.timeout_add_seconds(3, self._show_stimuli)

    def __post_trigger(self, msg_dict, retries=60):
        try:
            self._http_client.request("POST", "/",
                            body=pickle.dumps(msg_dict),
                            headers={'Accept': 'application/pickle'})
            response = self._http_client.getresponse()
            if response.status != 200:
                logging.error("Sending start trigger. Got HTTP status: {0} {1}".format(response.status, response.reason))
        except Exception as err:
            if retries == 0:
                retry_msg = "Gave up."
            else:
                retry_msg = "Re-trying."
            logging.error(f"Sending start failed. {retry_msg}. Error: {err}")
            if retries > 0:
                time.sleep(1)
                try:
                    # re-creating the connection, in case we've lost the connection
                    self._http_client = http.client.HTTPConnection(self._host, timeout=3)
                except Exception as err:
                    logging.error(f"Failed to re-create the HTTP connection: {err}")
                self.__post_trigger(msg_dict, retries=retries - 1)

    def _show_stimuli(self, *args):
        '''
        Showing stimuli
        '''
        logging.info("Stimuli {0} - {1}".format(self._stimuli_list[self._index],
                                                datetime.datetime.now()))
        image_path = STIMULI_PATH + self._stimuli_list[self._index]
        self.image_window.set_image(image_path)
        GLib.timeout_add_seconds(6, self._show_timer)

    def _show_timer(self, *args):
        '''
        Showing timer
        '''
        logging.info("Start of Conversation {0} - {1}".format(self._stimuli_list[self._index],
                                                              datetime.datetime.now()))

        timer = TimerWindow("Timer", message=EMOTIONS[self._stimuli_list[self._index][0]],
                            width=600,
                            font_size=20)
        timer.show_window()
        timer.connect("destroy", self._questionnaire)

    def _questionnaire(self, *args):
        logging.info(f"Sending STOP. Stimulus: {self._stimuli_list[self._index][:-4]}")
        self.__post_trigger({
            'type': 'STOP',
            'experiment_id': self._experiment_id,
            'stimulus_id': self._stimuli_list[self._index][:-4]})
        self._index += 1
        self._show_message(message="Please answer the questionnaire.")

    def _done(self, *args):
        logging.info("Sending TERMINATE.")
        self.__post_trigger({
            'type': 'TERMINATE',
            'experiment_id': self._experiment_id,
            'stimulus_id': 0})
        self.image_window.set_image("images/done_image.jpg")
        self.image_window.show_and_destroy_window(3)
        self.image_window.connect("destroy", self._terminate)

    def _terminate(self, *args):
        logging.info("End time{0}".format(datetime.datetime.now()))
        self.destroy()


def get_input_parameters():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--subject_id", help="The subject ID", default=0)
    #parser.add_argument("-t", "--task_id", help="The task ID", default=1)
    args = parser.parse_args()
    subject_id = args.subject_id
    task_id = 1  # args.task_id
    return subject_id, task_id


def main():
    subject_id, task_id = get_input_parameters()
    experiment_id = str(subject_id).zfill(2) + "-" + str(task_id).zfill(2)

    # Make delay for initializing all processes
    time.sleep(5)

    main_window = BackgroudWindow(experiment_id, subject_id, "172.24.16.32:9331")
    main_window.show()


main()
