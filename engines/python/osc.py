import sys
import liblo

etc = None 
osc_server = None
osc_target = None
osc_target2 = None

cc_last = [0] * 5
pgm_last = 0
notes_last = [0] * 128
clk_last = 0

# OSC callbacks
def fallback(path, args):
    pass

def echo1(path, args, type, src, data):
    fn = data
    globals()[fn](path, args)
    send(path, args[0])

def fs_callback(path, args):
    global etc
    v = args
    if (v[0] > 0):
        etc.foot_pressed()

def midicc_callback(path, args):
    global etc, cc_last
    val, num = args
    #print "midi cc: " + str(num) + " " + str(val)
    i = num - 21
    if i >= 0 and i < len(cc_last) and val != cc_last[i] :
        etc.cc_override_knob(i, float(val) / 127)
        cc_last[i] = val

def midinote_callback(path, args):
    global etc
    num, val = args
    #print "midi note: " + str(num) + " " + str(val)
    if val > 0 :
        etc.midi_notes[num] = 1
    else :
        etc.midi_notes[num] = 0

def trig_callback(path, args) :
    global etc
    etc.audio_trig = True

def audio_scale_callback(path, args):
    global etc
    val = args[0]
    etc.audio_scale = float(val)

def audio_trig_enable_callback(path, args):
    global etc
    val = args[0]
    if val == 1 : etc.audio_trig_enable = True
    else : etc.audio_trig_enable = False

def link_present_callback(path, args):
    global etc
    val = args[0]
    if val == 1 : etc.link_connected = True
    else : etc.link_connected = False
    # using this a sign of life of the pd patch:
    if not(etc.params_sent_pd):
        etc.recall_shift_params()
        send_params_pd()

def mblob_callback(path, args):
    global etc, cc_last, pgm_last, notes_last, clk_last
    midi_blob = args[0]
    
    for i in range(0, 5) :
        cc = midi_blob[16 + i]
        if cc != cc_last[i] :
            etc.cc_override_knob(i, float(cc) / 127)
            cc_last[i] = cc
            
    clk = midi_blob[21]
    if (clk != clk_last):
        etc.midi_clk = midi_blob[21]
        clk_last = clk

    pgm = midi_blob[22]
    if (pgm != pgm_last):
        etc.midi_pgm = pgm
        pgm_last = pgm

    # parse the notes outta the bit field
    for i in range(0, 16) :
        for j in range(0, 8) :
            if midi_blob[i] & (1<<j) :
                if(notes_last[(i*8)+j] != 1) : 
                    etc.midi_notes[(i * 8) + j] = 1
                    notes_last[(i*8)+j] = 1
            else :
                if(notes_last[(i*8)+j] != 0) : 
                    etc.midi_notes[(i * 8) + j] = 0
                    notes_last[(i*8)+j] = 0

def set_callback(path, args):
    global etc
    name = args[0]
    etc.set_mode_by_name(name)
    print "set patch to: " + str(etc.mode) + " with index " + str(etc.mode_index)
 
def new_callback(path, args):
    global etc
    name = args[0]
    etc.load_new_mode(name)
   
def reload_callback(path, args):
    global etc
    print "reloading: " + str(etc.mode)
    etc.reload_mode()

def midi_ch_callback(path, args):
    global etc
    val = args[0]
    etc.midi_ch = val
    send("/midi_ch", val)

def trigger_source_callback(path, args):
    global etc
    val = args[0]
    etc.trigger_source = val
    if val == 0 : etc.audio_trig_enable = True
    else : etc.audio_trig_enable = False
    send("/trigger_source", val)

def knobs_callback(path, args):
    global etc
    k1, k2, k3, k4, k5, k6 = args
    #print "received message: " + str(args)
    etc.knob_hardware[0] = float(k1) / 1023
    etc.knob_hardware[1] = float(k2) / 1023
    etc.knob_hardware[2] = float(k3) / 1023
    etc.knob_hardware[3] = float(k4) / 1023
    etc.knob_hardware[4] = float(k5) / 1023

def knob1_callback(path, args):
    global etc
    k1 = args[0]
    #print "received message: k1 " + str(args)
    etc.knob_hardware[0] = float(k1) / 1023
def knob2_callback(path, args):
    global etc
    k2 = args[0]
    #print "received message: k2 " + str(args)
    etc.knob_hardware[1] = k2 / 1023
def knob3_callback(path, args):
    global etc
    k3 = args[0]
    #print "received message: k3 " + str(args)
    etc.knob_hardware[2] = k3 / 1023
def knob4_callback(path, args):
    global etc
    k4 = args[0]
    #print "received message: k4 " + str(args)
    etc.knob_hardware[3] = k4 / 1023
def knob5_callback(path, args):
    global etc
    k5 = args[0]
    #print "received message: k5 " + str(args)
    etc.knob_hardware[4] = k5 / 1023

def shift_callback(path, args) :
    global etc
    stat = int(args[0])
    print "shift: " + str(stat)
    if stat == 1 : 
        etc.shift = True
        etc.set_osd(False)
        send("/shift", stat)
    else : 
        etc.shift = False
        etc.save_shift_params()
    print "shift: " + str(etc.shift)

def shift_line_callback(path, args) :
    global etc
    k = args[0]
    etc.shift_line[k] = " " + str(k + 1) + ": "
    for item in args[1:] :
        etc.shift_line[k] += " " + str(item)
    etc.shift_line[k] += " "

def quit_callback(path, args):
    global etc
    etc.quit = True

def keys_callback(path, args) :
    global etc
    k, v = args
    if (k == 5 and v > 0) : etc.next_mode()
    if (k == 4 and v > 0) : etc.prev_mode()
    if (k == 10) : etc.update_trig_button(v)
    if (k == 9 and v > 0) : etc.screengrab_flag = True
    if (k == 6 and v > 0) : etc.prev_scene()
    if (k == 8) : etc.save_or_delete_scene(v)
    if (k == 7 and v > 0) : etc.next_scene()
    if (k == 1 and v > 0) : 
        if (etc.osd) : etc.set_osd(False)
        else : etc.set_osd(True)
    if (k == 3 and v > 0) :
        if (etc.auto_clear) : etc.auto_clear = False
        else : etc.auto_clear = True

def skey_callback(path, args) :
    splitpath = path.split("/")
    k = int(splitpath[2])
    v = int(args[0])
    keys_callback(path, [k,v])

def init (etc_object) :
    global osc_server, osc_target, osc_target2, etc
    etc = etc_object
    
    # OSC init server and client
    try:
        osc_target = liblo.Address(4001)
        osc_target2 = liblo.Address(4002)
    except liblo.AddressError as err:
        print(err)

    try:
        osc_server = liblo.Server(4000)
    except liblo.ServerError, err:
        print str(err)
    
    # added methods for TouchOsc template as it cannot send two arguments
    osc_server.add_method("/knobs/1", 'f', echo1, "knob1_callback")
    osc_server.add_method("/knobs/2", 'f', echo1, "knob2_callback")
    osc_server.add_method("/knobs/3", 'f', echo1, "knob3_callback")
    osc_server.add_method("/knobs/4", 'f', echo1, "knob4_callback")
    osc_server.add_method("/knobs/5", 'f', echo1, "knob5_callback")
    osc_server.add_method("/key/1", 'f', skey_callback)
    osc_server.add_method("/key/3", 'f', skey_callback)
    osc_server.add_method("/key/4", 'f', skey_callback)
    osc_server.add_method("/key/5", 'f', skey_callback)
    osc_server.add_method("/key/6", 'f', skey_callback)
    osc_server.add_method("/key/7", 'f', skey_callback)
    osc_server.add_method("/key/8", 'f', skey_callback)
    osc_server.add_method("/key/9", 'f', skey_callback)
    osc_server.add_method("/key/10", 'f', skey_callback)

    # original osc methods
    osc_server.add_method("/knobs", 'iiiiii', knobs_callback)
    osc_server.add_method("/key", 'ii', keys_callback)
    osc_server.add_method("/mblob", 'b', mblob_callback)
    osc_server.add_method("/midicc", 'ii', midicc_callback)
    osc_server.add_method("/midinote", 'ii', midinote_callback)
    osc_server.add_method("/reload", 'i', reload_callback)
    # osc_server.add_method("/new", 's', reload_callback)
    osc_server.add_method("/set", 's', set_callback)
    osc_server.add_method("/new", 's', new_callback)
    osc_server.add_method("/fs", 'i', fs_callback)
    osc_server.add_method("/shift", 'i', shift_callback)
    osc_server.add_method("/ascale", 'f', echo1, "audio_scale_callback")
    osc_server.add_method("/trig", 'i', trig_callback)
    osc_server.add_method("/atrigen", 'i', audio_trig_enable_callback)
    osc_server.add_method("/linkpresent", 'i', link_present_callback)
    osc_server.add_method("/midi_ch", 'i', echo1, "midi_ch_callback")
    osc_server.add_method("/trigger_source", 'i', echo1, "trigger_source_callback")
    osc_server.add_method("/sline", None, shift_line_callback)
    osc_server.add_method("/quit", None, quit_callback)
    osc_server.add_method(None, None, fallback)

def recv() :
    global osc_server
    while (osc_server.recv(1)):
        pass

def send(addr, args) :
    global osc_target, osc_target2
    liblo.send(osc_target, addr, args)
    liblo.send(osc_target2, addr, args) 

def send_params_pd():
    global etc
    send("/trigger_source", etc.trigger_source)
    send("/midi_ch", etc.midi_ch)
    etc.params_sent_pd = True
