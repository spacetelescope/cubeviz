from __future__ import absolute_import, division, print_function

import numpy as np 
import sys

import astropy.units as u
from astropy import convolution

from glue.core import Data
from glue.core.coordinates import coordinates_from_header

from spectral_cube import SpectralCube, masks
import radio_beam

__all__ = ["data_to_cube", "cube_to_glueData", "get_kernel_list", "print_kernel_types"]

def data_to_cube(data, component_id=None, wcs=None):
	if type(data) == Data:
		if component_id is None:
			raise Exception("WCS information was not provided. "
				"use data_to_cube(data, component_id=<component id>).")
		w = data.coords.wcs
		d = data[component_id]
		m = masks.LazyMask(np.isfinite, data=d, wcs=w)
		cube = SpectralCube(data=d, wcs=w, mask=m)
	elif type(data) == np.ndarray:
		if wcs is None:
			raise Exception("WCS information was not provided. "
				"use data_to_cube(data, wcs=<wcs info>).")
		m = masks.LazyMask(np.isfinite, data=data, wcs=wcs)
		cube = SpectralCube(data=data, wcs=wcs, mask=m)
	elif type(data) == SpectralCube:
		cube = data
	else:
		raise TypeError("Input data is not supported.")

	return cube

def cube_to_glueData(cube, output_label="SmoothedCube", component_id="Cube"):
	result = Data(label=output_label)
	result.coords = coordinates_from_header(cube.header) 
	result.add_component(cube._data, component_id) 
	return result

def get_kernel_list():
	"""
	Registered kernels are stored here. Format is nested dict:
	kernel_list = {
		<kernel name> : {<"spatial"/"spectral">: <kernel obj>, <"spatial"/"spectral">: <kernel obj>},
		.
		.
		.
		<kernel name> : {<"spatial"/"spectral">: <kernel obj>}
	}
	If no kernels are available or needed for that smoothing option, None can be used as a place holder to 
	signify that axis can be used without a kernel function. In such cases, smoothing.smooth function needs
	to be modified to include the new spectral_cube.SpectralCube smoothing function.  

	Returns
	-------
	kernel_list : dict (nested)
		Dictionary of registered filter kernels.

	"""
	kernel_list ={
		"boxcar" : {"spatial" : convolution.Box2DKernel, "spectral" : convolution.Box1DKernel},
		"box" : {"spatial" : convolution.Box2DKernel, "spectral" : convolution.Box1DKernel},
		"gaussian" : {"spatial" : convolution.Gaussian2DKernel, "spectral" : convolution.Gaussian1DKernel},
		"mexicanhat": {"spatial" : convolution.MexicanHat2DKernel, "spectral" : convolution.MexicanHat1DKernel},
		"trapezoid": {"spatial" : convolution.TrapezoidDisk2DKernel, "spectral" : convolution.Trapezoid1DKernel},
		"trapezoiddisk": {"spatial" : convolution.TrapezoidDisk2DKernel},
		"arrydisk": {"spatial" : convolution.AiryDisk2DKernel},
		"ring" : {"spatial" : convolution.Ring2DKernel},
		"tophat" :{"spatial" : convolution.Tophat2DKernel},
		"median" : {"spatial" : None, "spectral" : None}
	}
	return kernel_list

def print_kernel_types():
	kernel_list = get_kernel_list()
	kernel_type_list = kernel_list.keys()
	print()
	print("Available Kernel Types")
	print("kernel_type: {available smoothing_axis}")
	print("_"*30)
	for kt in kernel_type_list:
		ax = kernel_list[kt].keys()
		print(str(kt)+": "+"{"+", ".join([str(a) for a in ax])+"}")

def _smoothing_available(kernel_type, smoothing_axis):
	try:
		if kernel_type == "median":
			if smoothing_axis == "spatial":
				SpectralCube.spatial_smooth_median
			else:
				SpectralCube.spectral_smooth_median
		else:
			if smoothing_axis == "spatial":
				SpectralCube.spatial_smooth
			else:
				SpectralCube.spectral_smooth
	except AttributeError as e:
		return False, e
	return True, None

def smooth(data, custom_kernel=None, kernel_type="boxcar", smoothing_axis="spatial", 
	kernel_size=3, component_id="SCI", output_label=None, wcs=None):
	"""
	This is a smoothing function for astronomical 3D Cube data. This function
	uses the smoothing functions provided by spectral_cube.SpectralCube to
	preform smoothing operations. This function can smooth in the spectral
	or spatial axes depending on the kernel applied. Select kernels from 
	astropy.convolution are available. To see a list of kernels and axes,
	please use the print_kernel_types() function. A custom kernel can also
	be used so long as it satisfies spectral_cube.SpectralCube as described
	by spectral_cube documentation. 

	Parameters
	----------
	data : glue.core.Data or numpy.ndarray or SpectralCube
		3D data to smooth. Accepted formats: 
		- Glue data object containing cube and wcs information. 
		- numpy ndarray (Must include WCS information).
		- SpectralCube instance with data.
	custom_kernel : astropy.convolution.kernels.<Kernel>
		Filter kernel from astropy. Can be subclassed.
	kernel_type : str
		Name of filter kernel. Use print_kernel_types() to see list.
	smoothing_axis : str
		'spectral' vs 'spatial' axis. Use print_kernel_types() to see 
		kernel compatibility.
	kernel_size : float
		Size of filter kernel.
	component_id : str
		Name of glue.core.Data component containing data.
	output_label: str
		label of output glue.core.Data.
	wcs : astropy.wcs.WCS
		wcs information. Required when input data is numpy ndarray!

	Returns
	-------
	output : glue.core.Data or numpy.ndarray or SpectralCube
		A smoothed cube that is the same type as input.

	Raises
	------
	Exception: If input kernel_type is not registered.
	Exception: If input smoothing_axis is not supported by filter kernel.
	AttributeError: 
		If missing smoothing functions in spectral_cube.SpectralCube.
		User is informed to update their spectral_cube.
	"""
	if custom_kernel is None:
		kernel_list = get_kernel_list()

		kernel_type_list = [i for i in kernel_list.keys()]
		kernel_type = kernel_type.strip().lower()
		if kernel_type not in kernel_type_list:
			print("Error: kernel_type was not understood. List of available options:")
			print_kernel_types()
			raise Exception("kernel_type was not understood.")

		smoothing_axis_list = [i for i in kernel_list[kernel_type].keys()]
		if smoothing_axis not in smoothing_axis_list:
			print("Error: smoothing_axis is not available. List of available axes for %s:" % kernel_type)
			for a in smoothing_axis_list:
				print(a)
			print("")
			raise Exception("smoothing_axis is not available for kernel_type %s." % kernel_type)

		available, exception = _smoothing_available(kernel_type, smoothing_axis)
		if not available:
			raise AttributeError("Please update your spectral-cube package, "+str(exception))
		if kernel_type == "median":
			kernel = None
		else:
			kernel_function = kernel_list[kernel_type][smoothing_axis]
			kernel = kernel_function(kernel_size)
	else:
		kernel = custom_kernel
		kernel_type = "custom_kernel"

	cube = data_to_cube(data, component_id, wcs)

	if kernel_type == "median":
		if smoothing_axis == "spatial":
			new_cube = cube.spatial_smooth_median()
		else:
			new_cube = cube.spectral_smooth_median()
	else:
		if smoothing_axis == "spatial":
			new_cube = cube.spatial_smooth(kernel)
		else:
			new_cube = cube.spectral_smooth(kernel)

	if type(data) == Data:
		if output_label is None:
			output_label = data.label+"_"
			output_label += "_".join([kernel_type, smoothing_axis])
		if component_id is None:
			component_id = "DataCube"
		output = cube_to_glueData(new_cube, output_label, component_id)
	elif type(data) == np.ndarray:
		output = np.copy(new_cube._data)
	else:
		output = new_cube

	return output
