from __future__ import absolute_import, division, print_function

import numpy as np 
import sys
import multiprocessing

import astropy.units as u
from astropy import convolution

from glue.core import Data
from glue.core.coordinates import coordinates_from_header
from glue.config import menubar_plugin

from spectral_cube import SpectralCube, masks
import radio_beam

from qtpy.QtCore import Qt
from qtpy.QtWidgets import (QMainWindow, QApplication, QPushButton,
							QLabel, QWidget, QHBoxLayout, QVBoxLayout,
							QComboBox, QMessageBox, QLineEdit)

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
	new_cube = cube.spatial_smooth_median(k_size)
	return cube_to_data(new_cube)

def median_kernel_spectral(data, k_size):
	cube = data_to_cube(data)
	new_cube = cube.spectral_smooth_median(k_size)
	return cube_to_data(new_cube)


def fail_test(data, k_size):
	cube = data_to_cube(data)
	new_cube = cube.dummy(k_size)
	return cube_to_data(new_cube)

def smoothing_process(data, k_size, method, queue, finished):
	"""
	Function to be used by multiprocessing.process. It 
	will call one of the smoothing functions and send back
	a glue Data object containing the result.

	Parameters
	----------
	data : glue.Data
		Glue data object containing cube and wcs information.
	k_size : int
		Kernel size.
	method : function
		Smoothing function.
	queue : multiprocessing.Queue
		Queue used for interprocess data communication.
	finished : multiprocessing.Event
		Event used to signal that this process 
		has completed its task. 
	"""
	try:
		new_data = method(data, k_size)
		queue.put(new_data)
		finished.set()
	except Exception as e:
		queue.put(str(e))
		finished.set()


class SelectSmoothing(QMainWindow):
	def __init__(self, data, data_collection, parent=None):
		super(SelectSmoothing,self).__init__(parent)#,Qt.WindowStaysOnTopHint)
		self.title = "Smoothing Selection"
		self.data = data
		self.data_collection = data_collection
		self.running = True

		self.sp = None #Smoothing process
		self.queue = multiprocessing.Queue()
		self.sp_finished = multiprocessing.Event()

		self.abort_window = None
		self.parent = parent

		self.init_Selection_UI()

	def init_Selection_UI(self):

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
		self.okButton.clicked.connect(self.main)
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

	def init_Abort_UI(self):
		self.abort_window = QMainWindow(parent=self.parent)

		self.label4 = QLabel("Executing smoothing algorithm.")
		self.label5 = QLabel("This may take several minutes.")

		self.abort = QPushButton("Abort")
		self.abort.clicked.connect(self.clean_up)

		vbl = QVBoxLayout()
		vbl.addWidget(self.label4)
		vbl.addWidget(self.label5)
		vbl.addWidget(self.abort)

		self.wid_abort = QWidget(self.abort_window)
		self.abort_window.setCentralWidget(self.wid_abort)
		self.wid_abort.setLayout(vbl)

		self.abort_window.show()

	def selection_changed(self, i):
		"""
		Update kernel type, units, etc... when
		smoothing function selection changes.
		"""
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

	def main(self):
		"""
		This function will create a multiprocessing.Process to
		call the smoothing function. It will validate the input 
		and assign a process to preform smoothing. While smoothing 
		is running, this function will update the application and
		host a gui with an abort button. It will remain in this state
		until smoothing is finished or the abort button is clicked. 
		"""
		success, k_size = self.input_validation()

		if not success:
			return

		self.hide()
		self.cancelButton.setDisabled(True) 
		self.okButton.setDisabled(True) 
		
		i = self.combo.currentIndex()

		self.sp = multiprocessing.Process(target=smoothing_process,
										  args=(self.data, 
										  		k_size,
										  		self.methods[i], 
										  		self.queue, 
										  		self.sp_finished)
										  )
		self.sp.start()

		self.init_Abort_UI()

		while not self.sp_finished.is_set() and self.running:
			QApplication.processEvents()
		
		if not self.running:
			return
		
		new_data = self.queue.get()
		self.sp_finished.clear()
		self.sp.join()
		
		if type(new_data) is str:
			e = new_data
			if "'SpectralCube' object has no attribute" in str(e):
				info = QMessageBox.critical(None, "Error",
						"Please update your spectral-cube package.\n"+str(e))
			else:
				info = QMessageBox.critical(None, "Error", str(e))
			self.abort_window.close()
			self.abort_window = None

			self.cancelButton.setDisabled(False) 
			self.okButton.setDisabled(False) 
			self.show()
			return

		self.data_collection.append(new_data)

		self.clean_up()

	def cancel(self, caller=0):
		self.clean_up()

	def isrunning(self):
		return self.running

	def clean_up(self):
		if self.sp is not None:
			if self.sp.is_alive():
				print("SelectSmoothing to child process: terminate()")
				self.sp.terminate()
		
		if self.abort_window is not None:
			self.abort_window.close()

		self.queue.close()
		self.close()
		self.running = False

@menubar_plugin("Smoothing")
def select_smoothing(session, data_collection):
	print(data_collection)
	data = data_collection[0]
	ex = SelectSmoothing(data, data_collection,parent=session.application)
	

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










