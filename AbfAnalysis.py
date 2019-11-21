import matplotlib.pyplot as plt
import pyabf as pyabf
import numpy as np
from fitting import *


class ActiveAbf:
    def __init__(self, abf_file):
        self._abf_data = pyabf.ABF(abf_file)
        self._abf_file_path = abf_file
        self._data_points_per_sec = self._abf_data.dataRate
        self._sweeps = self._abf_data.sweepCount

    def sweep_count(self):
        return self._abf_data.sweepCount

    def which_abf_file(self):
        return self._abf_file_path

    def get_sweep_voltages(self):
        sweep_voltages = {}
        for sweepNumber in range(self._sweeps):
            self._abf_data.setSweep(sweepNumber)
            sweep_voltages[sweepNumber] = self._abf_data.sweepC[round(len(self._abf_data.sweepC) / 2)]
        return sweep_voltages

    def get_raw_abf_data(self):
        some_data = {}
        for sweepNumber in range(self._sweeps):
            self._abf_data.setSweep(sweepNumber)
            some_data[sweepNumber] = {
                'sweep number': sweepNumber,
                'sweep currents (ADC)': self._abf_data.sweepY,
                'sweep input voltages (DAC)': self._abf_data.sweepC,
                'sweep times (seconds)': self._abf_data.sweepX
            }
        return some_data


class sweep(ActiveAbf):
    def __init__(self, abf_file, sweep_nr):
        super().__init__(abf_file)
        self._abf_data.setSweep(sweep_nr)
        self.t_clamp_on = self._abf_data.sweepEpochs.p1s[1] * self._abf_data.dataSecPerPoint
        self.t_shutter_on = self._abf_data.sweepEpochs.p1s[2] * self._abf_data.dataSecPerPoint
        self.t_shutter_off = self._abf_data.sweepEpochs.p1s[3] * self._abf_data.dataSecPerPoint
        self.t_clamp_off = self._abf_data.sweepEpochs.p1s[4] * self._abf_data.dataSecPerPoint
        self._currents = self._abf_data.sweepY
        self._currents_title = self._abf_data.sweepLabelY
        self._times = self._abf_data.sweepX
        self._times_title = self._abf_data.sweepLabelX
        self._input_voltage = self._abf_data.sweepC
        self._input_voltage_title = 'Digital Input Clamp Voltage (mV)'
        self._abf_data.setSweep(sweep_nr, 1)
        self._voltages = self._abf_data.sweepY
        self._voltages_title = self._abf_data.sweepLabelY
        self._abf_data.setSweep(sweep_nr, 2)
        self._shutter = self._abf_data.sweepY
        self._shutter_title = 'Shutter Voltage (V)'

    def get_sweep_data(self):
        return {
            'currents': self._currents,
            'currents title': self._currents_title,
            'times': self._times,
            'times title': self._times_title,
            'voltages': self._voltages,
            'voltages title': self._voltages_title,
            'shutter': self._shutter,
            'shutter title': self._shutter_title,
            'shutter on': self.t_shutter_on,
            'shutter off': self.t_shutter_off,
            'clamp on': self.t_clamp_on,
            'clamp off': self.t_clamp_off,
            'input clamp voltage': self._input_voltage,
            'input clamp voltage title': self._input_voltage_title
        }

    def set_corrected_currents(self, corrected_currents):
        assert corrected_currents.shape == self._currents.shape, 'new currents do not have the same shape as the ' \
                                                                 'previous ones '
        self._currents = corrected_currents


def correct_current_via_pre_light_fit(sweep, initial_function='exponential'):
    sweep_data = sweep.get_sweep_data()
    sweep_times = sweep_data['times']
    sweep_currents = sweep_data['currents']
    best_function, pre_light_fit_result = fit_pre_light(sweep, initial_function, make_plot=False)
    pre_light_fit_baseline = estimate_data_with_fit(sweep_times, best_function, pre_light_fit_result)
    baseline_corrected_currents = sweep_currents - pre_light_fit_baseline
    return baseline_corrected_currents


def correct_current_via_pre_and_after_light_fit(sweep, initial_function_pre_light='exponential',
                                                initial_function_after_light='exponential'):
    sweep_data = sweep.get_sweep_data()
    sweep_times = sweep_data['times']
    sweep_currents = sweep_data['currents']
    pre_light_best_function, pre_light_fit_result = fit_pre_light(sweep, initial_function_pre_light, make_plot=False)
    pre_light_fit_baseline = estimate_data_with_fit(sweep_times, pre_light_best_function, pre_light_fit_result)
    pre_light_baseline_corrected_currents = sweep_currents - pre_light_fit_baseline
    sweep.set_corrected_currents(pre_light_baseline_corrected_currents)
    after_light_best_function, after_light_fit_result = fit_after_light(sweep, initial_function_after_light,
                                                                        make_plot=True)
    after_light_fit_baseline = estimate_data_with_fit(sweep_times, after_light_best_function, after_light_fit_result)
    baseline_corrected_currents = sweep_currents - after_light_fit_baseline
    return baseline_corrected_currents


def plot_sweep(sweep, plot_interval=None, corrected=False):
    if plot_interval is None:
        plot_interval = [0, -1]
    else:
        assert (type(plot_interval) == list and len(plot_interval) == 2)
    sweep_data = sweep.get_sweep_data()
    if not corrected:
        time = sweep_data['times']
        current = sweep_data['currents']
        voltage = sweep_data['voltages']
    elif corrected == 'pre_light_only':
        time = sweep_data['times']
        current = correct_current_via_pre_light_fit(sweep)
        voltage = sweep_data['voltages']
    elif corrected == 'pre_and_after_light':
        time = sweep_data['times']
        current = correct_current_via_pre_and_after_light_fit(sweep)
        voltage = sweep_data['voltages']
    else:
        raise ValueError('corrected should be bool: False / pre_light_only / pre_and_after_light. Is, however, ', corrected)
    fig, axs = plt.subplots(2)
    axs[0].plot(time[plot_interval[0]:plot_interval[1]], current[plot_interval[0]:plot_interval[1]])
    axs[0].set(xlabel=sweep_data['times title'], ylabel=sweep_data['currents title'])
    axs[1].plot(time[plot_interval[0]:plot_interval[1]], voltage[plot_interval[0]:plot_interval[1]])
    axs[1].set(xlabel=sweep_data['times title'], ylabel=sweep_data['voltages title'])

    for ax in axs.flat:
        ax.label_outer()  # Hide x labels and tick labels for top plots and y ticks for right plots.
        ax.grid(alpha=.2)
        ax.axvspan(sweep_data['shutter on'], sweep_data['shutter off'], color='orange', alpha=.3, lw=0)

    plt.show()


def plot_all_sweeps(ActiveAbf, plot_interval=None, corrected=False):
    if plot_interval is None:
        plot_interval = [0, -1]
    else:
        assert (type(plot_interval) == list and len(plot_interval) == 2)
    nr_of_sweeps = ActiveAbf.sweep_count()
    fig, axs = plt.subplots(2)
    for i in range(nr_of_sweeps):
        sweepNumber = nr_of_sweeps - 1 - i
        sweep_interation = sweep(ActiveAbf.which_abf_file(), sweepNumber)
        sweep_data = sweep_interation.get_sweep_data()
        if not corrected:
            time = sweep_data['times']
            current = sweep_data['currents']
            voltage = sweep_data['voltages']
        elif corrected == 'pre_light_only':
            time = sweep_data['times']
            current = correct_current_via_pre_light_fit(sweep_interation)
            voltage = sweep_data['voltages']
        elif corrected == 'pre_and_after_light':
            time = sweep_data['times']
            current = correct_current_via_pre_and_after_light_fit(sweep_interation)
            voltage = sweep_data['voltages']
        else:
            raise ValueError('corrected should be bool: True / False . Is, however,', type(corrected))
        axs[0].plot(time[plot_interval[0]:plot_interval[1]], current[plot_interval[0]:plot_interval[1]], alpha=.5,
                    label="{} mV".format(sweep_data['input clamp voltage'][round(len(
                        sweep_data['input clamp voltage']) / 2)]))
        axs[1].plot(time[plot_interval[0]:plot_interval[1]], voltage[plot_interval[0]:plot_interval[1]], alpha=.5)
        axs[0].legend()
        if sweepNumber == 0:
            axs[0].set(xlabel=sweep_data['times title'], ylabel=sweep_data['currents title'])
            axs[1].set(xlabel=sweep_data['times title'], ylabel=sweep_data['voltages title'])
            for ax in axs.flat:
                ax.label_outer()  # Hide x labels and tick labels for top plots and y ticks for right plots.
                ax.grid(alpha=.2)
                ax.axvspan(sweep_data['shutter on'], sweep_data['shutter off'], color='orange', alpha=.3, lw=0)
    plt.show()
