"""Dispersion due to the solar wind."""
from __future__ import absolute_import, division, print_function

from warnings import warn

import astropy.constants as const
import astropy.units as u
import numpy as np

import pint.utils as ut
from pint.models.dispersion_model import Dispersion, DMconst
from pint.models.parameter import floatParameter
from pint.toa_select import TOASelect


class SolarWindDispersion(Dispersion):
    """Dispersion due to the solar wind (basic model).

    The model is a simple spherically-symmetric model that varies
    only in its amplitude.

    References
    ----------
    Edwards et al. 2006, MNRAS, 372, 1549; Setion 2.5.4
    Madison et al. 2019, ApJ, 872, 150; Section 3.1.

    """

    register = True
    category = "solar_wind"

    def __init__(self):
        super(SolarWindDispersion, self).__init__()
        self.add_param(
            floatParameter(
                name="NE_SW",
                units="cm^-3",
                value=0.0,
                aliases=["NE1AU", "SOLARN0"],
                description="Solar Wind Parameter",
            )
        )
        self.add_param(
            floatParameter(
                name="SWM", value=0.0, units="", description="Solar Wind Model"
            )
        )
        self.dm_value_funcs += [self.solar_wind_dm]
        self.delay_funcs_component += [self.solar_wind_delay]
        self.set_special_params(["NE_SW", "SWM"])

    def setup(self):
        super(SolarWindDispersion, self).setup()
        self.register_dm_deriv_funcs(self.d_dm_d_ne_sw, "NE_SW")
        self.register_deriv_funcs(self.d_delay_d_ne_sw, "NE_SW")

    def validate(self):
        super(SolarWindDispersion, self).validate()

    def solar_wind_geometry(self, toas):
        """ Return the geometry of solar wind dispersion.

        Implements the geometry part of equations 29, 30 of Edwards et al. 2006,
        (i.e., without the n0, the solar wind DM amplitude part.)
        Their rho is given as theta here.

        rvec: radial vector from observatory to the center of the Sun
        pos: pulsar position
        """
        tbl = toas.table
        rvec = tbl["obs_sun_pos"].quantity
        pos = self.ssb_to_psb_xyz_ICRS(epoch=tbl["tdbld"].astype(np.float64))
        r = np.sqrt(np.sum(rvec * rvec, axis=1))
        cos_theta = (np.sum(rvec * pos, axis=1) / r).to(u.Unit(""))
        theta = np.arccos(cos_theta).to(
            u.Unit(""), equivalencies=u.dimensionless_angles()
        )
        solar_wind_geometry = (
            const.au ** 2.0 * theta / (r * np.sqrt(1.0 - cos_theta ** 2.0))
        )
        return solar_wind_geometry

    def solar_wind_dm(self, toas):
        """Return the solar wind dispersion measure using equations
        29, 30 of Edwards et al. 2006.
        """
        if self.SWM.value == 0:
            solar_wind_geometry = self.solar_wind_geometry(toas)
            solar_wind_dm = self.NE_SW.quantity * solar_wind_geometry
        else:
            # TODO Introduce the You et.al. (2007) Solar Wind Model for SWM=1
            raise NotImplementedError(
                "Solar Dispersion Delay not implemented for SWM %d" % self.SWM.value
            )
        return solar_wind_dm.to(u.pc / u.cm ** 3)

    def solar_wind_delay(self, toas, acc_delay=None):
        """ This is a wrapper function to compute solar wind dispersion delay.
        """
        return self.dispersion_type_delay(toas)

    def d_dm_d_ne_sw(self, toas, param_name, acc_delay=None):
        """ Derivative of of DM wrt the solar wind dm amplitude.
        """
        if self.SWM.value == 0:
            solar_wind_geometry = self.solar_wind_geometry(toas)
        else:
            # TODO Introduce the You et.al. (2007) Solar Wind Model for SWM=1
            raise NotImplementedError(
                "Solar Dispersion Delay not implemented for SWM %d" % self.SWM.value
            )
        return solar_wind_geometry

    def d_delay_d_ne_sw(self, toas, param_name, acc_delay=None):
        try:
            bfreq = self.barycentric_radio_freq(toas)
        except AttributeError:
            warn("Using topocentric frequency for dedispersion!")
            bfreq = tbl["freq"]
        deriv = self.d_delay_d_dmparam(toas, "NE_SW")
        deriv[bfreq < 1.0 * u.MHz] = 0.0
        return deriv

    def print_par(self,):
        result = ""
        result += getattr(self, "NE_SW").as_parfile_line()
        result += getattr(self, "SWM").as_parfile_line()
        return result
