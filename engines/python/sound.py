import alsaaudio, audioop
import time
import math
import jack
import numpy

class DummyAlsaPort(object):
    def read(self):
        return (0,'')

inp = None
etc = None
trig_this_time = 0
trig_last_time = 0
sin = [0] * 100

def init (etc_object, AOUT_JACK) :

    global aout_jack, inp, client, etc, trig_this_time, trig_last_time, sin
    aout_jack = AOUT_JACK
    etc = etc_object

    if aout_jack:
        jack_connected = False
        # set up jack for sound in
        client = jack.Client("eyesy_jack_client", servername="default")
        client.inports.register('input_1')
        client.inports.register('input_2')
        client.blocksize = 512
        client.activate()
        while not(jack_connected):
            try:
                client.connect('crone:output_1', 'eyesy_jack_client:input_1')
                client.connect('crone:output_2', 'eyesy_jack_client:input_2')
                jack_connected = True
            except:
                pass
        time.sleep(1)
        inp = [
            client.get_port_by_name('eyesy_jack_client:input_1'),
            client.get_port_by_name('eyesy_jack_client:input_2')
        ]
    else:
        #setup alsa for sound in
        if etc.device == "dummy":
            inp = DummyAlsaPort()
        else:
            inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE,alsaaudio.PCM_NONBLOCK,device=etc.device)
            inp.setchannels(2) 
            inp.setrate(etc.rate)       # set to appropriate amount for soundcard .. OR 44100 / 48000
            inp.setformat(alsaaudio.PCM_FORMAT_S16_LE)
            inp.setperiodsize(etc.period)  # OR 1024

    trig_last_time = time.time()
    trig_this_time = time.time()
    for i in range(0,100) :
        sin[i] = int(math.sin(2 * 3.1459 * i / 100) * 32700)


def recv() :
    global client, inp, etc, trig_this_time, trig_last_time, sin
    if aout_jack:
        # get audio (with 16 bit signed format)
        data_l = 32767 * inp[0].get_array()
        data_r = 32767 * inp[1].get_array()
    else:
        # get audio from alsa
        l,data = inp.read()
        if l > 0:
            ldata = audioop.tomono(data, 2, 1, 0)
            rdata = audioop.tomono(data, 2, 0, 1)
    peak = 0
    # try :
    for i in range(0,100) :
        avg_l = 0
        avg_r = 0
        for j in range(3):
            if aout_jack:
                avg_l += data_l[3 * i + j]
                avg_r += data_r[3 * i + j]
            else:
                if l > 0:
                    try:
                        avg_l +=audioop.getsample(ldata, 2, (i * 3) + j)
                        avg_r +=audioop.getsample(rdata, 2, (i * 3) + j)
                    except audioop.error as e:
                        pass

    # except :
    #     pass

        avg_l = avg_l / 3
        avg_r = avg_r / 3

        avg = (avg_l + avg_r) / 2

        # scale it
        avg = int(avg * etc.audio_scale)
        avg_l = int(avg_l * etc.audio_scale)
        avg_r = int(avg_r * etc.audio_scale)

        if (avg > 20000) :
            trig_this_time = time.time()
            if (trig_this_time - trig_last_time) > .05:
                if etc.audio_trig_enable: etc.audio_trig = True
                trig_last_time = trig_this_time
        if avg > peak :
            etc.audio_peak = avg
            peak = avg
        # if the trigger button is held
        if (etc.trig_button) :
            etc.audio_in[i] = sin[i]
            etc.audio_left[i] = sin[i] 
            etc.audio_right[i] = sin[i] 
        else :
            etc.audio_in[i] = avg
            etc.audio_left[i] = avg_l
            etc.audio_right[i] = avg_r
