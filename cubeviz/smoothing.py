from __future__ import absolute_import, division, print_function

import numpy as np 

import astropy.units as u
from astropy import convolution

from glue.core import Data
from glue.core.coordinates import coordinates_from_header

from spectral_cube import SpectralCube, masks
import radio_beam

from qtpy.QtWidgets import *
from qtpy.QtCore import Qt
import sys
from glue.config import menubar_plugin
from time import sleep

def mask_function(arr):
	a = np.empty_like(arr)
	a.fill(True)
	a = a.astype(bool)
	return a

def data_to_cube(data, component_id="SCI"):
	w = data.coords.wcs
	d = data[component_id]
	m = masks.LazyMask(mask_function, data=d, wcs=w)
	cube = SpectralCube(data=d, wcs=w, mask=m)
	return cube

def cube_to_data(cube, name='SpectralCube', component_id="SCI"):
	#TODO: Usdate output data format	
	result = Data(label=name)
	result.coords = coordinates_from_header(cube.header) 
	result.add_component(cube._data, component_id) 
	return result

def boxcar_smoothing_spatial(data, k_size):
	cube = data_to_cube(data)
	kernel = convolution.Box2DKernel(k_size)
	new_cube = cube.spatial_smooth(kernel)	
	return cube_to_data(new_cube)

def boxcar_smoothing_spectral(data, k_size):
	cube = data_to_cube(data)
	kernel = convolution.Box1DKernel(k_size)
	new_cube = cube.spectral_smooth(kernel)	
	return cube_to_data(new_cube)

def gaussian_kernel_spatial(data, k_size):
	cube = data_to_cube(data)
	kernel = convolution.Gaussian2DKernel(k_size)
	new_cube = cube.spatial_smooth(kernel)	
	return cube_to_data(new_cube)

def gaussian_kernel_spectral(data, k_size):
	cube = data_to_cube(data)
	kernel = convolution.Gaussian1DKernel(k_size)
	new_cube = cube.spectral_smooth(kernel)	
	return cube_to_data(new_cube)

def median_kernel_spatial(data, k_size):
	cube = data_to_cube(data)
	new_cube = spatial_smooth_median(k_size)
	return cube_to_data(new_cube)

def median_kernel_spectral(data, k_size):
	cube = data_to_cube(data)
	new_cube = spectral_smooth_median(k_size)
	return cube_to_data(new_cube)

class SelectSmoothing(QMainWindow):
	def __init__(self, data, data_collection, parent=None):
		super(SelectSmoothing,self).__init__(parent)
		self.title = "Smoothing Selection"
		self.data = data
		self.data_collection = data_collection
		self.initUI()

	def initUI(self):

		self.methods = [
			boxcar_smoothing_spatial,
			boxcar_smoothing_spectral,
			gaussian_kernel_spatial,
			gaussian_kernel_spectral,
			median_kernel_spatial,
			median_kernel_spectral
			] 

		self.label1 = QLabel("Smoothing Type:")
		self.label1.setAlignment(Qt.AlignLeft)

		self.combo = QComboBox()
		self.combo.addItems([
			"Boxcar Kernel (Spatial Axes)",
			"Boxcar Kernel (Spectral Axis)",
			"Gaussian Kernel (Spatial Axes)",
			"Gaussian Kernel (Spectral Axis)",
			"Median Kernel (Spatial Axes)",
			"Median Kernel (Spectral Axis)"
			])

		self.combo.currentIndexChanged.connect(self.selection_changed)

		hbl1 = QHBoxLayout()
		hbl1.addWidget(self.label1)
		hbl1.addWidget(self.combo)

		self.label2 = QLabel("Width of Kernel:")
		self.label3 = QLabel("Pixels")
		self.k_size = QLineEdit("3")

		hbl2 = QHBoxLayout()
		hbl2.addWidget(self.label2)
		hbl2.addWidget(self.k_size)
		hbl2.addWidget(self.label3)


		self.okButton = QPushButton("OK")
		self.okButton.clicked.connect(self.ok)
		self.okButton.setDefault(True)

		self.cancelButton = QPushButton("Cancel")
		self.cancelButton.clicked.connect(self.cancel)

		hbl3 = QHBoxLayout()
		hbl3.addStretch(1)
		hbl3.addWidget(self.cancelButton)
		hbl3.addWidget(self.okButton)

		vbl = QVBoxLayout()
		vbl.addLayout(hbl1)
		vbl.addLayout(hbl2)
		vbl.addLayout(hbl3)

		self.wid = QWidget(self)
		self.setCentralWidget(self.wid)
		self.wid.setLayout(vbl)

		self.show()

	def selection_changed(self, i):
		if self.methods[i] in [gaussian_kernel_spatial,gaussian_kernel_spectral]:
			self.label2.setText("Standard Deviation of Kernel:")
		else:
			self.label2.setText("Width of Kernel:")

	def input_validation(self):
		if self.k_size == "":
			self.k_size.setStyleSheet("background-color: rgba(255, 0, 0, 128);")
			return False, None
		else:
			try:
				k_size = int(self.k_size.text())
			except ValueError:
				self.k_size.setStyleSheet("background-color: rgba(255, 0, 0, 128);")
				return False, None
			if k_size <= 0:
				return False, None
			self.k_size.setStyleSheet("")

		return True, k_size

	def ok(self):
		success, k_size = self.input_validation()

		if not success:
			return

		i = self.combo.currentIndex()		
		try:
			new_data = self.methods[i](self.data, k_size)
		except Exception as e:
			print(e)
			if "'SpectralCube' object has no attribute" in str(e):
				info = QMessageBox.critical(self, "Error",
						"Please update your spectral-cube package.\n"+str(e))
			else:
				info = QMessageBox.critical(self, "Error", str(e))
			return
	
		self.data_collection.append(new_data)
		self.close()

	def cancel(self):
		self.close()



@menubar_plugin("Smoothing")
def select_smoothing(session, data_collection):
	print(data_collection)
	data = data_collection[0]
	ex = SelectSmoothing(data, data_collection, parent=session.application)

if __name__ == "__main__":
	from sys import argv
	from glue.core.data_factories import load_data
	from glue.core import DataCollection

	dc = DataCollection()
	dc.append(load_data(argv[1]))

	data = dc[0]

	app = QApplication([])
	ex = SelectSmoothing(data, dc)
	sys.exit(app.exec_())










