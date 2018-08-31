from cascade.input_data.configuration.abstract_form import (
    _Form,
    IntegerField,
    FloatField,
    StringField,
    StringAsListField,
    OptionField,
    FormList,
    DummyForm,
)


class Distribution(_Form):
    density = OptionField(["uniform", "gaussian", "laplace", "students", "log_gaussian", "log_laplace", "log_students"])
    min = FloatField(nullable=True)
    mean = FloatField(nullable=True)
    max = FloatField(nullable=True)
    std = FloatField(nullable=True)


class SmoothingPrior(_Form):
    prior_type = OptionField(["dage", "dtime", "value"])
    age_lower = FloatField()
    age_upper = FloatField()
    time_lower = FloatField()
    time_upper = FloatField()
    density = OptionField(["uniform", "gaussian", "laplace", "students", "log_gaussian", "log_laplace", "log_students"])
    min = FloatField(nullable=True)
    mean = FloatField(nullable=True)
    max = FloatField(nullable=True)
    std = FloatField(nullable=True)


class SmoothingPriorGroup(_Form):
    dage = SmoothingPrior(name_field="prior_type")
    dtime = SmoothingPrior(name_field="prior_type")
    value = SmoothingPrior(name_field="prior_type")


class Smoothing(_Form):
    rate = IntegerField()
    age_grid = StringAsListField(" ", float)
    time_grid = StringAsListField(" ", float)
    default = SmoothingPriorGroup()
    mulstd = SmoothingPrior()
    detail = FormList(SmoothingPrior)

    custom_age_grid = DummyForm()
    custom_time_grid = DummyForm()


class Model(_Form):
    modelable_entity_id = IntegerField()
    title = StringField()
    description = StringField()
    bundle_id = IntegerField()
    drill = OptionField(["cascade", "drill"])
    drill_location = IntegerField()
    drill_sex = OptionField([1, 2], nullable=True)
    default_age_grid = StringAsListField(" ", float)
    default_time_grid = StringAsListField(" ", float)


class Configuration(_Form):
    model = Model()
    gbd_round_id = IntegerField()
    csmr_cod_output_version_id = IntegerField()
    csmr_mortality_output_version_id = IntegerField()
    location_set_version_id = IntegerField()
    random_effect = FormList(Smoothing)
    rate = FormList(Smoothing)

    min_cv = FormList(DummyForm)
    min_cv_by_rate = FormList(DummyForm)
    re_bound_location = FormList(DummyForm)
    study_covariate = DummyForm()
    country_covariate = DummyForm()
    derivative_test = DummyForm()
    max_num_iter = DummyForm()
    print_level = DummyForm()
    accept_after_max_steps = DummyForm()
    tolerance = DummyForm()
    students_dof = DummyForm()
    log_students_dof = DummyForm()
    eta = DummyForm()
    data_eta_by_integrand = DummyForm()
    data_density_by_integrand = DummyForm()
    config_version = DummyForm()
