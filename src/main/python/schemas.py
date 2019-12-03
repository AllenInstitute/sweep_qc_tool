from marshmallow import Schema
from marshmallow.fields import Float, Str, Integer, Boolean, Nested, DateTime, List, Dict, Tuple


class QcCriteria(Schema):
    pre_noise_rms_mv_max = Float(description="noise voltage (mV) before to stimulus, sweep-level gate")
    post_noise_rms_mv_max = Float(description="noise voltage (mV) after stimulus, sweep-level gate")
    slow_noise_rms_mv_max = Float(description="patch instability voltage (mV) before stimulus , sweep-level gate")
    vm_delta_mv_max = Float(description="voltage (mV) difference between beginning and end of sweep, sweep-level gate")
    leak_pa_min = Float(description="min bias current (pA), sweep-level gate")
    leak_pa_max = Float(description="max bias current (pA), sweep-level gate")

    blowout_mv_min = Float(description="min blowout voltage (mV) cell-level gate")
    blowout_mv_max = Float(description="max blowout voltage (mV), cell-level gate")
    seal_gohm_min = Float(description="min seal resistance (GOhm), cell-level gate")
    access_resistance_mohm_min = Float(description="min access resistance (MOhm), cell-level gate")
    access_resistance_mohm_max = Float(description="max access resistance (MOhm), cell-level gate")
    input_vs_access_resistance_max = Float(description="max of input vs access resistance")
    electrode_0_pa_min = Float(description="min baseline (electrode zero) current (pA), cell-level gate")
    electrode_0_pa_max = Float(description="max baseline (electrode zero) current (pA), cell-level gate")

    created_at = DateTime(description="datetime when criteria created")
    updated_at = DateTime(description="datetime when criteria updated")
    id = Integer(description="criteria id")
    name = Str(description="criteria name")


class ManualSweepState(Schema):
    sweep_number = Integer(description="sweep number", required=True)
    sweep_state = Str(description="manual override state", required=True)


class SweepParameters(Schema):
    stimulus_code = Str(description="stimulus code", required=True)
    stimulus_name = Str(description="index of sweep in order of presentation", required=True)
    stimulus_amplitude = Float(description="amplitude of stimulus", required=True, allow_none=True)
    sweep_number = Integer(description="index of sweep in order of presentation", required=True)
    stimulus_units = Str(desription="stimulus units", required=True)
    bridge_balance_mohm = Float(description="bridge balance", allow_none=True)
    pre_vm_mv = Float(allow_none=True)
    leak_pa = Float(allow_none=True)
    passed = Boolean(description="qc passed or failed", required=True)


class CellParameters(Schema):
    blowout_mv = Float(description="blowout voltage (mV)", required=False, allow_none=True)
    seal_gohm = Float(description="seal resistance (GOhm)", allow_none=True)
    electrode_0_pa = Float(description="electrode zero current (pA)", allow_none=True)
    input_access_resistance_ratio = Float(description="input vs access resistance ratio", allow_none=True)
    input_resistance_mohm = Float(description="input resistance (Mohm)", allow_none=True)
    initial_access_resistance_mohm = Float(description="initial access resistance (Mohm)", allow_none=True)


class PipelineParameters(Schema):
    input_nwb_file = Str(description="input nwb file", required=True)
    stimulus_ontology_file = Str(description="stimulus ontology JSON", required=False)
    qc_criteria = Nested(QcCriteria, required=False)
    manual_sweep_states = Nested(ManualSweepState, required=False, many=True)
    ipfx_version = Str(description="version of ipfx package")


class FeaturesExtractionParameters(Schema):
    input_nwb_file = Str(description="input nwb file", required=True)
    stimulus_ontology_file = Str(description="stimulus ontology JSON", required=False)
    output_nwb_file = Str(description="output nwb file", required=True)
    qc_fig_dir = Str(description="output qc figure directory", required=False)
    sweep_features = Nested(SweepParameters, many=True)
    cell_features = Nested(CellParameters, required=True)


# definitions used by FxOutput
class SpikeFeatures(Schema):
    threshold_index = Integer()
    clipped = Boolean()
    threshold_t = Float()
    threshold_v = Float()
    threshold_i = Integer()
    peak_index = Integer()
    peak_t = Float()
    peak_v = Float()
    peak_i = Integer()
    trough_index = Integer()
    trough_t = Float()
    trough_v = Float()
    trough_i = Integer()
    upstroke_index = Integer()
    upstroke = Float()
    upstroke_t = Float()
    upstroke_v = Float()
    downstroke_index = Integer()
    downstroke = Float()
    downstroke_t = Float()
    downstroke_v = Float()
    isi_type = Str()
    fast_trough_index = Integer()
    fast_trough_t = Float()
    fast_trough_v = Float()
    fast_trough_i = Integer()
    adp_index = Integer(allow_none=True)
    adp_t = Float(allow_none=True)
    adp_v = Float(allow_none=True)
    adp_i = Integer(allow_none=True)
    slow_trough_index = Integer(allow_none=True)
    slow_trough_t = Float(allow_none=True)
    slow_trough_v = Float(allow_none=True)
    slow_trough_i = Integer(allow_none=True)
    width = Float()
    upstroke_downstroke_ratio = Float()


class FirstSpikeMeanFeatures(Schema):
    upstroke_downstroke_ratio = Float()
    peak_v = Float()
    peak_t = Float()
    trough_v = Float()
    trough_t = Float()
    fast_trough_v = Float(allow_none=True)
    fast_trough_t = Float(allow_none=True)
    slow_trough_v = Float(allow_none=True)
    slow_trough_t = Float(allow_none=True)
    threshold_v = Float()
    threshold_i = Integer()
    threshold_t = Float()


class SweepFeatures(Schema):
    avg_rate = Float()
    peak_deflect = Tuple((Float(), Integer()))
    stim_amp = Float()
    v_baseline = Float()
    sag = Float()
    adapt = Float(allow_none=True)
    latency = Float(allow_none=True)
    isi_cv = Float(allow_none=True)
    mean_isi = Float(allow_none=True)
    median_isi = Float(allow_none=True)
    first_isi = Float(allow_none=True)
    index = Integer()
    sweep_number = Integer()
    tau = Integer()
    spikes = Nested(SpikeFeatures, many=True)


class LongSquareFeatures(Schema):
    v_baseline = Float()
    rheobase_i = Float()
    fi_fit_slope = Float()
    sag = Float()
    vm_for_sag = Float()
    input_resistance = Float()
    sweeps = Nested(SweepFeatures, many=True)
    tau = Float()
    rheobase_sweep = Nested(SweepFeatures)
    spiking_sweeps = Nested(SweepFeatures, many=True)
    hero_sweep = Nested(SweepFeatures)
    subthreshold_sweeps = Nested(SweepFeatures, many=True)
    subthreshold_membrane_property_sweeps = Nested(SweepFeatures, many=True)


class ShortSquareFeatures(Schema):
    stimulus_amplitude = Float()
    common_amp_sweeps = Nested(SweepFeatures, many=True)
    mean_spike_0 = Nested(FirstSpikeMeanFeatures)


class RampFeatures(Schema):
    spiking_sweeps = Nested(SweepFeatures, many=True)
    mean_spike_0 = Nested(FirstSpikeMeanFeatures)


class CellFeatures(Schema):
    long_squares = Nested(LongSquareFeatures)
    short_squares = Nested(ShortSquareFeatures)
    ramps = Nested(RampFeatures)


class CellRecord(Schema):
    rheobase_sweep_num = Integer()
    thumbnail_sweep_num = Integer()
    vrest = Float()
    ri = Float()
    sag = Float()
    tau = Float()
    vm_for_sag = Float()
    f_i_curve_slope = Float()
    adaptation = Float()
    latency = Float()
    avg_isi = Float()
    upstroke_downstroke_ratio_long_square = Float()
    peak_v_long_square = Float()
    peak_t_long_square = Float()
    trough_v_long_square = Float()
    trough_t_long_square = Float()
    fast_trough_v_long_square = Float()
    fast_trough_t_long_square = Float()
    slow_trough_v_long_square = Float(allow_none=True)
    slow_trough_t_long_square = Float(allow_none=True)
    threshold_v_long_square = Float()
    threshold_i_long_square = Float()
    threshold_t_long_square = Float()
    upstroke_downstroke_ratio_ramp = Float()
    peak_v_ramp = Float()
    peak_t_ramp = Float()
    trough_v_ramp = Float()
    trough_t_ramp = Float()
    fast_trough_v_ramp = Float()
    fast_trough_t_ramp = Float()
    slow_trough_v_ramp = Float()
    slow_trough_t_ramp = Float()
    threshold_v_ramp = Float()
    threshold_i_ramp = Float()
    threshold_t_ramp = Float()
    upstroke_downstroke_ratio_short_square = Float()
    peak_v_short_square = Float()
    peak_t_short_square = Float()
    trough_v_short_square = Float()
    trough_t_short_square = Float()
    fast_trough_v_short_square = Float()
    fast_trough_t_short_square = Float()
    slow_trough_v_short_square = Float(allow_none=True)
    slow_trough_t_short_square = Float(allow_none=True)
    threshold_v_short_square = Float()
    threshold_i_short_square = Float()
    threshold_t_short_square = Float()
    input_access_resistance_ratio = Float()
    blowout_mv = Float(allow_none=True)
    electrode_0_pa = Float()
    seal_gohm = Float()
    input_resistance_mohm = Float()
    initial_access_resistance_mohm = Float()


class SweepRecord(Schema):
    pre_vm_mv = Float()
    bridge_balance_mohm = Float()
    stimulus_units = Str()
    stimulus_code = Str()
    stimulus_amplitude = Float()
    sweep_number = Integer()
    stimulus_name = Str()
    passed = Boolean()
    leak_pa = Float(allow_none=True)
    clamp_mode = Str()
    peak_deflection = Float(allow_none=True)
    num_spikes = Integer()


class CellState(Schema):
    failed_fx = Boolean()
    fail_fx_message = Str(allow_none=True)


class FeatureExtractionOutput(Schema):
    cell_features = Nested(CellFeatures)
    sweep_features = Dict(keys=Str(), values=Nested(SweepFeatures))
    cell_record = Nested(CellRecord)
    sweep_records = List(Nested(SweepRecord))
    cell_state = Nested(CellState)


