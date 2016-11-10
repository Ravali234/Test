import scipy.io
import numpy as np
import x6.process_waveform as pw
import matplotlib.pyplot as plt

def gen_velo_from_files(i_file, q_file, var_name='r', volt_units=False):

    output_file='single_pulse.velo'

    ysI = scipy.io.loadmat(i_file, variable_names=[var_name])[var_name]
    ysQ = scipy.io.loadmat(q_file, variable_names=[var_name])[var_name]

    if volt_units:
        ysI *= 2
        ysQ *= 2

    scaled_ysI = (2**15 - 1) * ysI
    scaled_ysQ = (2**15 - 1) * ysQ
    scaled_ysI = scaled_ysI.astype('<i2')
    scaled_ysQ = scaled_ysQ.astype('<i2')

    pw.waveform_to_velo([True,False,True,False],
        output_file,
        waveform0=pw.Waveform(scaled_ysI),
        waveform2=pw.Waveform(scaled_ysQ)
        )

def gen_velo_from_files2(mat_file, var_names=('x','y')):

    output_file='single_pulse.velo'

    pw.waveform_to_velo([True,False,True,False],
        output_file,
        waveform0=pw.Waveform(mat_file, var_name=var_names[0]),
        waveform2=pw.Waveform(mat_file, var_name=var_names[1])
    )

def gen_velo_single_pulse(
        pulse_width=100,
        pulse_phasedeg=0,
        phase_shift_degree=0,
        pulse_amp=1,
        num_avgs=1
    ):

    f = 200*10**6 # 200MHz carrier
    #f = 50*10**6
    w = f*2*np.pi
    f1 = 50*10**6 # 50 MHz
    w1 = f1*2*np.pi
    t_step = 10**-9 # 1ns timestep (1GSPs DAC rate)
    t_step2 = 10**-6

    output_file = 'single_pulse.velo'

    ts_pulse1 = np.arange(0,pulse_width)

  ##  ysI_pulse = pulse_amp*np.sin((w * ts_pulse1 * t_step) + (pulse_phasedeg * (np.pi / 180)))
 ##   ysQ_pulse = pulse_amp*np.cos((w * ts_pulse1 * t_step) + (pulse_phasedeg * (np.pi / 180)+(45*(np.pi/180))))
  ##  ysQ_pulse = pulse_amp*np.cos((w * ts_pulse1 * t_step) + (pulse_phasedeg * (np.pi / 180)+(phase_shift_degree*(np.pi/180))))
    a = np.random.rand()
    b = np.random.rand()

    ysI_pulse = pulse_amp*np.sin((w * ts_pulse1 * t_step) + (pulse_phasedeg * (np.pi / 180)))
    ysQ_pulse = pulse_amp*np.cos((w * ts_pulse1 * t_step) + (pulse_phasedeg * (np.pi / 180)+(phase_shift_degree*(np.pi/180))))
    #ysI_pulse = pulse_amp*np.sin((w * ts_pulse1 * t_step) + (pulse_phasedeg * (np.pi / 180))) + pulse_amp*np.sin(w1*ts_pulse1*t_step)
    #ysQ_pulse = pulse_amp*np.cos((w * ts_pulse1 * t_step) + (pulse_phasedeg * (np.pi / 180)+(phase_shift_degree*(np.pi/180))))+ pulse_amp*np.sin(w1*ts_pulse1*t_step)


    ysI = ysI_pulse
    ysQ = ysQ_pulse

    for idx in xrange(num_avgs-1):
        ysI = np.append(ysI, ysI_pulse)
        ysQ = np.append(ysQ, ysQ_pulse)

    scaled_ysI = (2**15 - 1) * ysI
    scaled_ysQ = (2**15 - 1) * (ysQ+10)
    scaled_ysI.astype('<i2')
    scaled_ysQ.astype('<i2')

    pw.waveform_to_velo([True,False,True,False],
                        output_file,
                        waveform0=pw.Waveform(scaled_ysI),
                        waveform2=pw.Waveform(scaled_ysQ)
                        )

    return ysI, ysQ
