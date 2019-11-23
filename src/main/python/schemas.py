from marshmallow import Schema, fields
from marshmallow.fields import Float, Str, Integer, Boolean, Nested, DateTime


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
    sweep_state = fields.String(description="manual override state", required=True)


class PipelineInput(Schema):
    input_nwb_file = Str(description="input nwb file", required=True)
    stimulus_ontology_file = Str(description="blash", required=False)
    input_h5_file = Str(desription="input h5 file", required=False)
    qc_criteria = Nested(QcCriteria, required=False)
    manual_sweep_states = Nested(ManualSweepState, required=False, many=True)
    ipfx_version = Str(description="version of ipfx package")
