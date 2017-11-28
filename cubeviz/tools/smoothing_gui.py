from __future__ import absolute_import, division, print_function

import numpy as np 
import sys

import astropy.units as u
from astropy import convolution

from glue.core import Data
from glue.core import message as msg
from glue.core.coordinates import coordinates_from_header
from glue.config import menubar_plugin

from spectral_cube import SpectralCube, masks
import radio_beam

from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
	QMainWindow, QApplication, QPushButton,
	QLabel, QWidget, QHBoxLayout, QVBoxLayout,
	QComboBox, QMessageBox, QLineEdit, QRadioButton
)

from . import smoothing


class SelectSmoothing(QMainWindow):
	def __init__(self, data, data_collection, parent=None):
		super(SelectSmoothing,self).__init__(parent)
		self.setWindowFlags(self.windowFlags() | Qt.Tool)
		self.title = "Smoothing Selection"
		self.data = data
		self.data_collection = data_collection
		self.component_id = "SCI"

		self.abort_window = None
		self.parent = parent

		self.currentAxes = None 
		self.currentKernel = None

		self.init_Selection_UI()

	def init_Selection_UI(self):

		self.label1 = QLabel("Smoothing Axes:")
		self.label1.setMinimumWidth(150)

		self.spatial_radio = QRadioButton("Spatial")
		self.spatial_radio.setChecked(True)
		self.currentAxes = "spatial"
		self.spatial_radio.toggled.connect(self.spatial_radio_checked)

		self.spectral_radio = QRadioButton("Spectral")
		self.spectral_radio.toggled.connect(self.spectral_radio_checked)

		hbl1 = QHBoxLayout()
		hbl1.addWidget(self.label1)
		hbl1.addWidget(self.spatial_radio)
		hbl1.addWidget(self.spectral_radio)


		self.label2 = QLabel("Kernel Type:")
		self.label2.setMinimumWidth(150)

		self.load_options()
		self.combo = QComboBox()
		self.combo.setMinimumWidth(150)
		self.combo.addItems(self.options["spatial"])
		

		hbl2 = QHBoxLayout()
		hbl2.addWidget(self.label2)
		hbl2.addWidget(self.combo)

		self.label3 = QLabel("Width of Kernel:")
		self.label3.setWordWrap(True)
		self.label3.setMinimumWidth(150)
		self.label4 = QLabel("Pixels")
		self.k_size = QLineEdit("1")

		hbl3 = QHBoxLayout()
		hbl3.addWidget(self.label3)
		hbl3.addWidget(self.k_size)
		hbl3.addWidget(self.label4)

		self.label5 = QLabel("Data Component:")
		self.label5.setWordWrap(True)
		self.label5.setMinimumWidth(150)

		component_ids = [str(i) for i in self.data.component_ids()]
		self.component_combo = QComboBox()
		self.component_combo.addItems(
			component_ids
			)
		self.component_combo.setMaximumWidth(150)

		hbl4 = QHBoxLayout()
		hbl4.addWidget(self.label5)
		hbl4.addWidget(self.component_combo)

		self.okButton = QPushButton("OK")
		self.okButton.clicked.connect(self.call_main)
		self.okButton.setDefault(True)

		self.cancelButton = QPushButton("Cancel")
		self.cancelButton.clicked.connect(self.cancel)

		hbl5 = QHBoxLayout()
		hbl5.addStretch(1)
		hbl5.addWidget(self.cancelButton)
		hbl5.addWidget(self.okButton)

		vbl = QVBoxLayout()
		vbl.addLayout(hbl1)
		vbl.addLayout(hbl2)
		vbl.addLayout(hbl3)
		vbl.addLayout(hbl4)
		vbl.addLayout(hbl5)
		
		self.wid = QWidget(self)
		self.setCentralWidget(self.wid)
		self.wid.setLayout(vbl)

		self.setMaximumWidth(330)

		self.combo.currentIndexChanged.connect(self.selection_changed)
		self.selection_changed(0)

		self.show()

	def init_Abort_UI(self):
		self.abort_window = QMainWindow(
			parent=self.parent,
			flags=Qt.WindowStaysOnTopHint)
		self.abort_window.setWindowFlags(
			self.abort_window.windowFlags() | Qt.Tool)

		self.labelA1 = QLabel("Executing smoothing algorithm.")
		self.labelA2 = QLabel("This may take several minutes.")

		vbl = QVBoxLayout()
		vbl.addWidget(self.labelA1)
		vbl.addWidget(self.labelA2)

		self.wid_abort = QWidget(self.abort_window)
		self.abort_window.setCentralWidget(self.wid_abort)
		self.wid_abort.setLayout(vbl)

		self.abort_window.show()

	def load_options(self):
		kernel_registry = smoothing.get_kernel_registry()

		self.options = {"spatial" : [], "spectral" : []}
		for k in kernel_registry:
			axis = kernel_registry[k]
			for a in axis:
				name = k
				if a == "spatial":
					self.options["spatial"].append(name)
				elif a == "spectral":
					self.options["spectral"].append(name)
		self.options["spectral"].sort()
		self.options["spatial"].sort()
		currentKernel= self.options[self.currentAxes][0]
		self.currentKernel = currentKernel

	def selection_changed(self, i):
		"""
		Update kernel type, units, etc... when
		smoothing function selection changes.
		"""
		keys = self.options[self.currentAxes]
		currentKernel = keys[i]
		if currentKernel in ["Gaussian"]:
			self.label3.setText("Standard Deviation of Kernel:")
		elif currentKernel in ["AiryDisk","Ring",
			"Tophat","TrapezoidDisk"]:
			self.label3.setText("Radius of Kernel:")
		else:
			self.label3.setText("Width of Kernel:")
		self.currentKernel = currentKernel

	def spatial_radio_checked(self):
		self.currentAxes = "spatial"
		self.combo.clear()
		self.combo.addItems(self.options["spatial"])

	def spectral_radio_checked(self):
		self.currentAxes = "spectral"
		self.combo.clear()
		self.combo.addItems(self.options["spectral"])

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

	def get_unique_name(self):
		"""
		Find a unique name for the resulting glue Data object.
		"""
		if len(self.data_collection) == 0:
			return "Smoothed Cube"
		return "Smoothed Cube"

		numbers = []
		for data in self.data_collection:
			if type(data) == Data:
				if "Smoothed Cube" in data.label:
					label = data.label.split("Smoothed Cube")
					if len(label) != 2:
						continue
					elif label[1] == '':
						numbers.append(0)
						continue
					else:
						try:
							i = int(label[1])
						except ValueError:
							continue
						numbers.append(i)
		if len(numbers) == 0:
			i = max(numbers) + 1
			return "Smoothed Cube %s" %(i)
		else:
			return "Smoothed Cube"
	
	def call_main(self):
		try:
			self.main()
		except Exception as e:
			info = QMessageBox.critical(self, "Error", str(e))
			self.cancel()
			raise

	def main(self):
		"""
		Main function to process input and call smoothing.smooth.
		"""
		success, k_size = self.input_validation()

		if not success:
			return

		component = str(self.component_combo.currentText())
		
		self.hide()
		self.init_Abort_UI()
		QApplication.processEvents()
				
		output = smoothing.smooth(
			self.data, 
			smoothing_axis=self.currentAxes, 
			kernel_type=self.currentKernel,
			kernel_size=k_size, 
			component_id=component, 
			output_as_component=True)

		info = QMessageBox.information(self, "Success", 
			"Result added as a new component of the input Data")
		
		self.abort_window.close()
		self.close()
	

	def cancel(self, caller=0):
		self.close()
		if self.abort_window is not None:
			self.abort_window.close()
