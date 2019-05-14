# -----------------------------------------------------------------------------
# Name:        cooper.py (part of PyGMI)
#
# Author:      Patrick Cole
# E-Mail:      pcole@geoscience.org.za
#
# Copyright:   (c) 2013 Council for Geoscience
# Licence:     GPL-3.0
#
# This file is part of PyGMI
#
# PyGMI is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyGMI is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# -----------------------------------------------------------------------------
""" This is a collection of routines by Gordon Cooper

|    School of Geosciences, University of the Witwatersrand
|    Johannesburg, South Africa
|    cooperg@geosciences.wits.ac.za
|    http://www.wits.ac.za/science/geophysics/gc.htm
"""

import copy
from PyQt5 import QtWidgets, QtCore
import numpy as np
import scipy.signal as si
import scipy.interpolate as si2

import pygmi.menu_default as menu_default


class Gradients(QtWidgets.QDialog):
    """
    Class used to gather information via a GUI, for function gradients

    Attributes
    ----------
    parent : parent
    indata : dictionary
        PyGMI input data in a dictionary
    outdata :
        PyGMI input data in a dictionary
    azi : float
        Azimuth/filter direction (degrees)
    elev : float
        Elevation (for sunshading, degrees from horizontal)
    order : int
        Order of DR filter - see paper. Try 1 first.
    """
    def __init__(self, parent):
        QtWidgets.QDialog.__init__(self, parent)

        self.parent = parent
        self.indata = {}
        self.outdata = {}
        self.azi = 45.
        self.elev = 45.
        self.order = 1
        self.pbar = self.parent.pbar

        self.sb_order = QtWidgets.QSpinBox()
        self.sb_azi = QtWidgets.QSpinBox()
        self.rb_ddir = QtWidgets.QRadioButton()
        self.rb_vgrad = QtWidgets.QRadioButton()
        self.rb_dratio = QtWidgets.QRadioButton()
        self.label_or = QtWidgets.QLabel()
        self.label_az = QtWidgets.QLabel()

        self.setupui()

        self.sb_azi.setValue(self.azi)
        self.sb_order.setValue(self.order)

    def setupui(self):
        """ Setup UI """
        gridlayout = QtWidgets.QGridLayout(self)
        buttonbox = QtWidgets.QDialogButtonBox()
        helpdocs = menu_default.HelpButton('pygmi.raster.cooper.gradients')

        self.sb_order.setMinimum(1)
        self.sb_azi.setPrefix("")
        self.sb_azi.setMinimum(-360)
        self.sb_azi.setMaximum(360)
        buttonbox.setOrientation(QtCore.Qt.Horizontal)
        buttonbox.setStandardButtons(buttonbox.Cancel | buttonbox.Ok)
        self.rb_ddir.setChecked(True)
        self.sb_order.hide()
        self.label_or.hide()

        self.setWindowTitle("Gradient Calculation")
        self.label_az.setText("Azimuth")
        self.label_or.setText("Strength Factor")
        self.rb_ddir.setText("Directional Derivative")
        self.rb_dratio.setText("Derivative Ratio")
        self.rb_vgrad.setText("Vertical Derivative")

        gridlayout.addWidget(self.rb_ddir, 0, 0, 1, 1)
        gridlayout.addWidget(self.rb_dratio, 1, 0, 1, 1)
        gridlayout.addWidget(self.rb_vgrad, 2, 0, 1, 1)
        gridlayout.addWidget(self.label_az, 3, 0, 1, 1)
        gridlayout.addWidget(self.sb_azi, 3, 1, 1, 1)
        gridlayout.addWidget(self.label_or, 4, 0, 1, 1)
        gridlayout.addWidget(self.sb_order, 4, 1, 1, 1)
        gridlayout.addWidget(helpdocs, 5, 0, 1, 1)
        gridlayout.addWidget(buttonbox, 5, 1, 1, 1)

        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        self.rb_ddir.clicked.connect(self.radiochange)
        self.rb_dratio.clicked.connect(self.radiochange)
        self.rb_vgrad.clicked.connect(self.radiochange)

    def settings(self):
        """ Settings """
        temp = self.exec_()
        if temp == 0:
            return False

        self.azi = self.sb_azi.value()
        self.order = self.sb_order.value()

        data = copy.deepcopy(self.indata['Raster'])

        for i in self.pbar.iter(range(len(data))):
            if self.rb_ddir.isChecked():
                data[i].data = gradients(data[i].data, self.azi)
            elif self.rb_dratio.isChecked():
                data[i].data = derivative_ratio(data[i].data, self.azi,
                                                self.order)
            else:
                mask = np.ma.getmaskarray(data[i].data)
                data[i].data = np.ma.array(vertical(data[i].data))
                data[i].data.mask = mask
            data[i].units = ''

        self.outdata['Raster'] = data

        return True

    def radiochange(self):
        """ Check radio button state """
        self.sb_order.hide()
        self.label_or.hide()
        self.sb_azi.hide()
        self.label_az.hide()

        if self.rb_dratio.isChecked():
            self.sb_order.show()
            self.label_or.show()
            self.sb_azi.show()
            self.label_az.show()
        elif self.rb_ddir.isChecked():
            self.sb_azi.show()
            self.label_az.show()


def gradients(data, azi):
    """
    Compute directional derivative of image data. Based on code by
    Gordon Cooper.

    Parameters
    ----------
    data : numpy array
        input numpy data array
    azi : float
        Filter direction (degrees)

    Returns
    -------
    dr : float
        returns derivative ratio
    """
    # Directional derivative

    azi = np.deg2rad(azi)
    dx, dy = np.gradient(data)
    dt1 = -dy*np.sin(azi)-dx*np.cos(azi)

    return dt1


def derivative_ratio(data, azi, order):
    """
    Compute derivative ratio of image data. Based on code by Gordon Cooper.

    Parameters
    ----------
    data : numpy array
        input numpy data array
    azi : float
        Filter direction (degrees)
    order : int
        Order of DR filter - see paper. Try 1 first.

    Returns
    -------
    dr : float
        returns derivative ratio
    """
    # Directional derivative

    azi = np.deg2rad(azi)
    dx, dy = np.gradient(data)
    dt1 = -dy*np.sin(azi)-dx*np.cos(azi)

    # Derivative ratio

    dt2 = -dy*np.sin(azi+np.pi/2)-dx*np.cos(azi+np.pi/2)
    dt2 = dt2.astype(np.float64)
    dr = np.arctan2(dt1, abs(dt2)**order)

    return dr


class Visibility2d(QtWidgets.QDialog):
    """
    Class used to gather information via a GUI, for function visibility2d

    Attributes
    ----------
    parent : parent
    indata : dictionary
        PyGMI input data in a dictionary
    outdata :
        PyGMI input data in a dictionary
    wsize : int
        window size, must be odd
    dh : float
        height of observer above surface
    """
    def __init__(self, parent):
        QtWidgets.QDialog.__init__(self, parent)

        self.parent = parent
        self.indata = {}
        self.outdata = {}
        self.wsize = 11
        self.dh = 10
        self.pbar = self.parent.pbar

        self.sb_dh = QtWidgets.QSpinBox()
        self.sb_wsize = QtWidgets.QSpinBox()

        self.setupui()

        self.sb_wsize.setValue(self.wsize)
        self.sb_dh.setValue(self.dh)

    def setupui(self):
        """ Setup UI """
        gridlayout = QtWidgets.QGridLayout(self)
        buttonbox = QtWidgets.QDialogButtonBox()
        helpdocs = menu_default.HelpButton('pygmi.raster.cooper.visibility')
        label = QtWidgets.QLabel()
        label_2 = QtWidgets.QLabel()

        self.sb_dh.setMinimum(1)
        self.sb_dh.setMaximum(10000)
        self.sb_wsize.setPrefix("")
        self.sb_wsize.setMinimum(3)
        self.sb_wsize.setMaximum(100000)
        self.sb_wsize.setSingleStep(2)
        buttonbox.setOrientation(QtCore.Qt.Horizontal)
        buttonbox.setStandardButtons(buttonbox.Cancel | buttonbox.Ok)

        self.setWindowTitle("Visibility")
        label.setText("Viewing Height (% std dev)")
        label_2.setText("Window Size (Odd)")

        gridlayout.addWidget(label_2, 0, 0, 1, 1)
        gridlayout.addWidget(self.sb_wsize, 0, 1, 1, 1)
        gridlayout.addWidget(label, 1, 0, 1, 1)
        gridlayout.addWidget(self.sb_dh, 1, 1, 1, 1)
        gridlayout.addWidget(helpdocs, 2, 0, 1, 1)
        gridlayout.addWidget(buttonbox, 2, 1, 1, 1)

        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)

    def settings(self):
        """ Settings """
        temp = self.exec_()
        if temp == 0:
            return False

        self.wsize = self.sb_wsize.value()
        self.dh = self.sb_dh.value()

        data = copy.deepcopy(self.indata['Raster'])
        data2 = []

        for i, datai in enumerate(data):
            self.parent.showprocesslog(datai.dataid+':')

            vtot, vstd, vsum = visibility2d(datai.data, self.wsize,
                                            self.dh*data[i].data.std()/100.,
                                            self.pbar.iter)
            data2.append(copy.deepcopy(datai))
            data2.append(copy.deepcopy(datai))
            data2.append(copy.deepcopy(datai))
            data2[-3].data = vtot
            data2[-2].data = vstd
            data2[-1].data = vsum
            data2[-3].dataid += ' Total Visibility'
            data2[-2].dataid += ' Visibility Variation'
            data2[-1].dataid += ' Visibility Vector Resultant'

        self.outdata['Raster'] = data2
        self.parent.showprocesslog('Finished!')

        return True


def visibility2d(data, wsize, dh, piter=iter):
    """
    Compute visibility as a textural measure

    Compute vertical derivatives by calculating the visibility at different
    heights above the surface (see paper)

    Parameters
    ----------
    data : numpy array
        input dataset - numpy MxN array
    wsize : int
        window size, must be odd
    dh : float
        height of observer above surface

    Returns
    -------
    vtot : numpy array
    vstd : numpy array
    vsum : numpy array
    """

    nr, nc = np.shape(data)
    wsize = abs(np.real(wsize))
    w2 = int(np.floor(wsize/2))
    vn = np.zeros([nr, nc])
    vs = np.zeros([nr, nc])
    ve = np.zeros([nr, nc])
    vw = np.zeros([nr, nc])
    vd1 = np.zeros([nr, nc])
    vd2 = np.zeros([nr, nc])
    vd3 = np.zeros([nr, nc])
    vd4 = np.zeros([nr, nc])
    vstd = np.zeros([nr, nc])
    mask = np.ma.getmaskarray(data)
    mean = data.mean()
    data = data.data
    data[mask] = mean

    for j in piter(range(nc)):    # Columns
        for i in range(w2, nr-w2):
            dtmp = data[i-w2:i+w2+1, j]
            vn[i, j] = __visible1(dtmp, wsize, w2+1, dh)
            vs[i, j] = __visible2(dtmp, w2+1, dh)

    for j in piter(range(w2, nc-w2)):    # Rows
        for i in range(nr):
            dtmp = data[i, j-w2:j+w2+1]
            ve[i, j] = __visible1(dtmp, wsize, w2+1, dh)
            vw[i, j] = __visible2(dtmp, w2+1, dh)

    for j in piter(range(w2, nc-w2)):
        for i in range(w2, nr-w2):
            dtmp = np.zeros(wsize)
            for k in range(wsize):
                dtmp[k] = data[i-w2+k, j-w2+k]
            vd1[i, j] = __visible1(dtmp, wsize, w2+1, dh)
            vd2[i, j] = __visible2(dtmp, w2+1, dh)
            dtmp = np.zeros(wsize)
            for k in range(wsize):
                dtmp[k] = data[i+w2-k, j-w2+k]
            vd3[i, j] = __visible1(dtmp, wsize, w2+1, dh)
            vd4[i, j] = __visible2(dtmp, w2+1, dh)

    vtot = vn+vs+ve+vw+vd1+vd2+vd3+vd4
    vtot = vtot[w2:nr-w2, w2:nc-w2]

    for j in piter(range(nc)):
        for i in range(nr):
            vstd[i, j] = np.std([vn[i, j], vs[i, j], ve[i, j], vw[i, j],
                                 vd1[i, j], vd2[i, j], vd3[i, j],
                                 vd4[i, j]], ddof=1)

    vstd = vstd[w2:nr-w2, w2:nc-w2]

    dtr = np.pi/180
    c45 = np.cos(45*dtr)
    s45 = np.sin(45*dtr)
    vsumx = ve-vw+vd1*c45-vd2*c45+vd3*c45-vd4*c45
    vsumy = vn-vs+vd1*s45-vd2*s45-vd3*s45+vd4*s45
    vsum = np.sqrt(vsumx*vsumx+vsumy*vsumy)
    vsum = vsum[w2:nr-w2, w2:nc-w2]

    vtot = np.ma.array(vtot)
    vstd = np.ma.array(vstd)
    vsum = np.ma.array(vsum)
    vtot.mask = mask[w2:-w2, w2:-w2]
    vstd.mask = mask[w2:-w2, w2:-w2]
    vsum.mask = mask[w2:-w2, w2:-w2]

    return vtot, vstd, vsum


def __visible1(dat, nr, cp, dh):
    """ Visible 1 """
    num = 1

    if cp < nr-1 and dat.size > 0:
        num = 2
        cpn = cp-1
        thetamax = float(dat[cpn+1]-dat[cpn]-dh)
        for i in range(cpn+2, nr):
            theta = ((dat[i]-dat[cpn]-dh)/float(i-cpn))
            if theta >= thetamax:
                num = num + 1
                thetamax = theta

    return num


def __visible2(dat, cp, dh):
    """ Visible 2 """
    num = 0

    if cp > 2 and dat.size > 0:
        num = 1
        cpn = cp-1
        thetamax = (dat[cpn-1]-dat[cpn]-dh)
        for i in range(cpn-2, -1, -1):
            theta = ((dat[i]-dat[cpn]-dh)/(cpn-i))
            if theta >= thetamax:
                num = num + 1
                thetamax = theta
    return num


class Tilt1(QtWidgets.QDialog):
    """
    Class used to gather information via a GUI, for function tilt1

    Attributes
    ----------
    parent : parent
    indata : dictionary
        PyGMI input data in a dictionary
    outdata :
        PyGMI input data in a dictionary
    azi : float
        directional filter azimuth in degrees from East
    smooth : int
        size of smoothing matrix to use - must be odd input 0 for no smoothing
    """
    def __init__(self, parent):
        QtWidgets.QDialog.__init__(self, parent)

        self.parent = parent
        self.indata = {}
        self.outdata = {}
        self.azi = 75
        self.smooth = 0
        self.pbar = self.parent.pbar

        self.sb_azi = QtWidgets.QSpinBox()
        self.sb_s = QtWidgets.QSpinBox()

        self.setupui()

        self.sb_s.setValue(self.smooth)
        self.sb_azi.setValue(self.azi)

    def setupui(self):
        """ Setup UI """
        gridlayout = QtWidgets.QGridLayout(self)
        buttonbox = QtWidgets.QDialogButtonBox()
        helpdocs = menu_default.HelpButton('pygmi.raster.cooper.tilt')
        label = QtWidgets.QLabel()
        label_2 = QtWidgets.QLabel()

        buttonbox.setOrientation(QtCore.Qt.Horizontal)
        buttonbox.setStandardButtons(buttonbox.Cancel | buttonbox.Ok)
        self.sb_azi.setMinimum(-360)
        self.sb_azi.setMaximum(360)
        self.sb_azi.setProperty("value", 0)
        self.sb_s.setPrefix("")
        self.sb_s.setMinimum(0)
        self.sb_s.setMaximum(100000)
        self.sb_s.setSingleStep(1)

        self.setWindowTitle("Tilt Angle")
        label.setText("Azimuth (degrees from east)")
        label_2.setText("Smoothing Matrix Size (Odd, 0 for None)")

        gridlayout.addWidget(label_2, 0, 0, 1, 1)
        gridlayout.addWidget(self.sb_s, 0, 1, 1, 1)
        gridlayout.addWidget(label, 1, 0, 1, 1)
        gridlayout.addWidget(self.sb_azi, 1, 1, 1, 1)
        gridlayout.addWidget(helpdocs, 2, 0, 1, 1)
        gridlayout.addWidget(buttonbox, 2, 1, 1, 1)

        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)

    def settings(self):
        """ Settings """
        temp = self.exec_()
        if temp == 0:
            return False

        self.smooth = self.sb_s.value()
        self.azi = self.sb_azi.value()

        data = copy.deepcopy(self.indata['Raster'])
        data2 = []

        for i in self.pbar.iter(range(len(data))):
            t1, th, t2, ta, tdx = tilt1(data[i].data, self.azi, self.smooth)
            data2.append(copy.deepcopy(data[i]))
            data2.append(copy.deepcopy(data[i]))
            data2.append(copy.deepcopy(data[i]))
            data2.append(copy.deepcopy(data[i]))
            data2.append(copy.deepcopy(data[i]))
            data2[-5].data = t1
            data2[-4].data = th
            data2[-3].data = t2
            data2[-2].data = ta
            data2[-1].data = tdx
            data2[-5].dataid += ' Standard Tilt Angle'
            data2[-4].dataid += ' Hyperbolic Tilt Angle'
            data2[-3].dataid += ' 2nd Order Tilt Angle'
            data2[-2].dataid += ' Tilt Based Directional Derivative'
            data2[-1].dataid += ' Total Derivative'

        for i in data2:
            i.data.data[i.data.mask] = i.nullvalue

        self.outdata['Raster'] = data2
        return True


def tilt1(data, azi, s):
    """
    Tilt angle calculations

    Parameters
    ----------
    data : numpy array
        matrix of double to be filtered
    azi : float
        directional filter azimuth in degrees from East
    s : int
        size of smoothing matrix to use - must be odd input 0 for no smoothing

    Returns
    -------
    t1 : numpy masked array
        Standard tilt angle
    th : numpy masked array
        Hyperbolic tilt angle
    t2 : numpy masked array
        2nd order tilt angle
    ta : numpy masked array
        Tilt Based Directional Derivative
    tdx : numpy masked array
        Total Derivative
    """

    dmin = data.min()
    dmax = data.max()
    dm = 0.5*(dmin+dmax)
    data.data[data.mask] = dm
    data[np.isnan(data)] = dm
    data[np.isinf(data)] = dm

    if s > 0:
        se = np.ones((s, s))/(s*s)
        data2 = si.convolve2d(data, se, 'valid')  # smooth
        mask = si.convolve2d(data.mask, se, 'valid')
        data = np.ma.array(data2, mask=mask)

    nr, nc = data.shape
    dtr = np.pi/180.0
    azi = azi*dtr

    dy, dx = np.gradient(data)
#    dx = dx.astype(np.float64)
#    dy = dy.astype(np.float64)
    dxtot = np.ma.sqrt(dx*dx+dy*dy)
    nmax = np.max([nr, nc])
    npts = int(2**nextpow2(nmax))
    dz = vertical(data, npts, 1)
    t1 = np.ma.arctan(dz/dxtot)
    th = np.real(np.arctanh(np.nan_to_num(dz/dxtot)+(0+0j)))
    tdx = np.real(np.ma.arctan(dxtot/abs(dz)))

    dx1 = dx*np.cos(azi)+dy*np.sin(azi)  # Standard directional derivative
    dx2 = dx*np.cos(azi+np.pi/2)+dy*np.sin(azi+np.pi/2)
    dxz = np.ma.sqrt(dx2*dx2+dz*dz)
    ta = np.ma.arctan(dx1/dxz)         # Tilt directional derivative

    # 2nd order Tilt angle

    ts = t1
    if s < 3:
        s = 3
    se = np.ones([s, s])/(s*s)
    ts = si.convolve2d(t1, se, 'same')
    [dxs, dys] = np.gradient(ts)
    dzs = vertical(ts, npts, 1)
    dxtots = np.ma.sqrt(dxs*dxs+dys*dys)
    t2 = np.ma.arctan(dzs/dxtots)

    # Standard tilt angle, hyperbolic tilt angle, 2nd order tilt angle,
    # Tilt Based Directional Derivative, Total Derivative
    t1 = np.ma.array(t1)
    th = np.ma.array(th)
    th.mask = np.ma.getmaskarray(t1)
    t2 = np.ma.array(t2)
    t2.mask = np.ma.getmaskarray(t1)
    ta = np.ma.array(ta)
    tdx = np.ma.array(tdx)

    return t1, th, t2, ta, tdx


def nextpow2(n):
    """ nextpow2 """
    m_i = np.ceil(np.log2(n))
    return m_i


def vertical(data, npts=None, xint=1):
    """ Vertical """

    nr, nc = data.shape

    z = data-np.ma.median(data)
    if np.ma.is_masked(z):
        z = z.filled(0.)

    if npts is None:
        nmax = np.max([nr, nc])
        npts = int(2**nextpow2(nmax))

    cdiff = int(np.floor((npts-nc)/2))
    rdiff = int(np.floor((npts-nr)/2))
    cdiff2 = npts-cdiff-nc
    rdiff2 = npts-rdiff-nr
#    data1 = __taper2d(data, npts, nc, nr, cdiff, rdiff)
    data1 = np.pad(z, [[rdiff, rdiff2], [cdiff, cdiff2]], 'edge')
#    data1 = data - np.median(data)
#    data1 = np.pad(data, [[rdiff, rdiff2], [cdiff, cdiff2]], 'linear_ramp',
#                   end_values=(0, 0))

    f = np.fft.fft2(data1)
    fz = f
    wn = 2.0*np.pi/(xint*(npts-1))
    f = np.fft.fftshift(f)
    cx = npts/2+1
    cy = cx
    for i in range(npts):
        freqx = (i+1-cx)*wn
        for j in range(npts):
            freqy = (j+1-cy)*wn
            freq = np.sqrt(freqx*freqx+freqy*freqy)
            fz[i, j] = f[i, j]*freq
    fz = np.fft.fftshift(fz)
    fzinv = np.fft.ifft2(fz)
    dz = np.real(fzinv[rdiff:nr+rdiff, cdiff:nc+cdiff])

    return dz


def __taper2d(g, npts, c, r, cdiff, rdiff):
    """ Taper 2D """

# n is cols, m is rows

    npts2 = npts-1
    gm = g.mean()
    gf = np.zeros([npts, npts])
    gf[rdiff:rdiff+r, cdiff:cdiff+c] = g-gm

    for i in range(cdiff):
        tmp = ((1+np.sin(-np.pi/2+i*np.pi/cdiff))*0.5)
        for j in range(rdiff, rdiff+r):
            gf[i, j] = gf[i, j]*tmp
            gf[npts2-i, j] = gf[npts2-i, j]*tmp

#    for j in range(rdiff):
#        tmp = ((1+np.sin(-np.pi/2+j*np.pi/(rdiff)))*0.5)
#        for i in range(cdiff, cdiff+c):
#            gf[i, j] = gf[i, j]*tmp
#            gf[i, npts2-j-1] = gf[i, npts2-j-1]*tmp
#
#    for i in range(cdiff):
#        tmp = ((1+np.sin(-np.pi/2+i*np.pi/(cdiff)))*0.5)
#        for j in range(rdiff):
#            gf[i, j] = gf[i, j]*tmp
#            gf[npts2-i, j] = gf[npts2-i, j]*tmp
#
#    for i in range(cdiff):
#        tmp = ((1+np.sin(-np.pi/2+i*np.pi/(cdiff)))*0.5)
#        for j in range(rdiff+m-1, npts):
#            gf[i, j] = gf[i, j]*tmp
#            gf[npts2-i, j] = gf[npts2-i, j]*tmp
#
#    for j in range(rdiff+m-1, npts):  # Corners
#        for i in range(cdiff+n-1, npts):
#            if cdiff == 0 or rdiff == 0:
#                gf[i, j] = np.nan
#            else:
#                gf[i, j] = (gf[i, j] *
#                            np.cos((i+1-cdiff-n)*np.pi/(2*cdiff)) *
#                            np.cos((j+1-cdiff-m)*np.pi/(2*rdiff)))
#
#    for j in range(rdiff):
#        for i in range(cdiff):
#            if cdiff == 0 or rdiff == 0:
#                gf[i, j] = np.nan
#            else:
#                gf[i, j] = (gf[i, j] *
#                            np.cos((i+1-cdiff)*np.pi/(2*cdiff)) *
#                            np.cos((j+1-cdiff)*np.pi/(2*rdiff)))
#
#    for j in range(rdiff):
#        for i in range(cdiff+n-1, npts):
#            if cdiff == 0 or rdiff == 0:
#                gf[i, j] = np.nan
#            else:
#                gf[i, j] = (gf[i, j] *
#                            np.cos((i+1-cdiff-n)*np.pi/(2*cdiff)) *
#                            np.cos((j+1-cdiff)*np.pi/(2*rdiff)))
#
#    for j in range(rdiff+m, npts):
#        for i in range(cdiff):
#            if cdiff == 0 or rdiff == 0:
#                gf[i, j] = np.nan
#            else:
#                gf[i, j] = (gf[i, j] *
#                            np.cos((i+1-cdiff)*np.pi/(2*cdiff)) *
#                            np.cos((j+1-cdiff-m)*np.pi/(2*rdiff)))

    return gf


def test():
    """ test routine """
    import pygmi.raster.iodefs as io
    import matplotlib.pyplot as plt

    ifile = r'C:\Work\Programming\pygmi\data\testdata.hdr'
    idat = io.get_raster(ifile)

    idat = idat[2]  # Get magnetic data
    z = idat.data
    nr, nc = z.shape

# Gridding test
#    y, x = np.mgrid[0:nr, 0:nc]
#    x1 = x[~z.mask]
#    y1 = y[~z.mask]
#    z1 = z[~z.mask]
#
#    z1 = z1-np.median(z1)
#
#    data = si2.griddata((x1, y1), z1, (x, y), 'nearest')

    data = z

    z2 = vertical(data)
    z2 = np.ma.array(z2, mask=z.mask)

    plt.figure(figsize=(8, 8))
    plt.title('original')
    plt.imshow(data)
    plt.colorbar()
    plt.show()

    plt.figure(figsize=(8, 8))
    plt.title('vertical')
    plt.imshow(z2, vmin=-2, vmax=2)
    plt.colorbar()
    plt.show()


    z2a = z2

# Gridding test 2
    y, x = np.mgrid[0:nr, 0:nc]
    x1 = x[~z.mask]
    y1 = y[~z.mask]
    z1 = z[~z.mask]

    npts = 512
    cdiff = int(np.floor((npts-nc)/2))
    rdiff = int(np.floor((npts-nr)/2))
    x1 = x1 + cdiff
    y1 = y1 + rdiff

    y, x = np.mgrid[0:npts, 0:npts]

    data = si2.griddata((x1, y1), z1, (x, y), 'nearest')
    z2 = vertical(data)
    rdiff = rdiff-1
    cdiff = cdiff-1
    z2 = z2[rdiff:rdiff+nr, cdiff:cdiff+nc]
    z2 = np.ma.array(z2, mask=z.mask)


    plt.figure(figsize=(8, 8))
    plt.title('original')
    plt.imshow(data)
    plt.colorbar()
    plt.show()

    plt.figure(figsize=(8, 8))
    plt.title('vertical')
    plt.imshow(z2, vmin=-2, vmax=2)
    plt.colorbar()
    plt.show()


    z2b = z2

    # Difference

    z3 = z2a-z2b

    plt.figure(figsize=(8, 8))
    plt.title('difference')
    plt.imshow(z3)
    plt.colorbar()
    plt.show()

    x = np.arange(-2*np.pi, 2*np.pi, 0.1)
    y = np.sinc(x)

    plt.plot(x, y)
    plt.show()

    z4 = z2.compressed()

    plt.hist(z4, 100)
    plt.show()


#    z2 = z.filled(0.)

#    x, y = np.mgrid[0:z.shape[0], 0:z.shape[1]]
#    x1 = x[~z.mask]
#    y1 = y[~z.mask]
#    z1 = z[~z.mask]
#
#    z2 = si2.griddata((x1, y1), z1, (x, y), 'linear', fill_value=0.0)
#
#    nr, nc = z2.shape
#
#    nmax = np.max([nr, nc])
#    npts = int(2**nextpow2(nmax))
#    cdiff = int(np.floor((npts-nc)/2))
#    rdiff = int(np.floor((npts-nr)/2))
#
#    z2 = z2*0 + np.random.rand(nr, nc)
#
#    z3 = __taper2d(z2, npts, nc, nr, cdiff, rdiff)
#
#
#    z2 = z.filled(0)

#    z3 = vertical(z)

#    ff = si2.interpolate.CloughTocher2DInterpolator

#    z3 = np.ma.array(z3, mask=z.mask)

    breakpoint()



if __name__ == "__main__":
    # doctest.testmod(pygmi.raster)
    test()
