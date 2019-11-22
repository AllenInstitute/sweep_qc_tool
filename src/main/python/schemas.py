from marshmallow import Schema, fields
from marshmallow.fields import Float, Str, Integer, Boolean, Nested, DateTime


class QcCriteria(Schema):
    pre_noise_rms_mv_max = Float()
    post_noise_rms_mv_max = Float()
    slow_noise_rms_mv_max = Float()
    vm_delta_mv_max = Float()
    blowout_mv_min = Float()
    blowout_mv_max = Float()
    electrode_0_pa_max = Float()
    seal_gohm_min = Float()
    input_vs_access_resistance_max = Float()
    access_resistance_mohm_min = Float()
    access_resistance_mohm_max = Float()
    updated_at = DateTime()
    leak_pa_max = Float()
    leak_pa_min = Float()
    electrode_0_pa_min = Float()
    created_at = DateTime()
    id = Integer()
    name = Str()


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
