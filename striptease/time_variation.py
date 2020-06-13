# -*- encoding: utf-8 -*-
import striptease as st
from striptease.hdf5files import DataFile
from matplotlib import pyplot as plt
import h5py
import pickle
import numpy as np
import matplotlib.patches as mpatches
import itertools
from astropy.time import TimeDelta
from astropy.time import Time 

tiles = ['B', 'G', 'I', 'O', 'R', 'V', 'Y']
boardX = ['BOARD_'+tt for tt in tiles]

polarimeterXY=['POL_'+tt+str(npol) for tt in tiles for npol in range(7)]
polarimeterXY.extend(['POL_W'+npol for npol in np.arange(1,7).astype(str)])


def lookfor_timevariation(vtime,step_ref=1.5,silent=True):
	"""
	This function analyzes the time variation, which looks for
	the ups and downs to identify: forwards, backwards and hat
	jumps in the time vector.
	
	--Parameters
	vtime : sci time string (astropy.time.Time object).

	step_ref : reference factor to define the threshold used
	in the jumps and downs. This value is multiply to the
	median of the first ten delta time string. The delta time
	string is defined as the subtraction of two consecutive
	time step.

	silent : True by default.
	
	--Return
	report : dictionary with all ups and downs (index and time),
			and features clasified as: hat, forward and backward 
			(index and time). In hat case, the start and end (indices
			and time) are saved as list (e.g. [index_start,index_end]).
	"""
	delt = vtime[1:].value.astype(float) - vtime[0:-1].value.astype(float)
	vmedian = np.median(delt[0:10])
	dd_ref = step_ref * vmedian

	ids_up = np.where(delt > dd_ref)[0]    # Ups
	ids_down = np.where(delt < -dd_ref)[0] # Downs
	
	nup = len(ids_up)
	ndown = len(ids_down)

	#
	idfor, idback = [], []
	idhat, idhat_start, idhat_end = [], [], []
	time_hat, time_for, time_back = [],[],[]
	duration_hat = []
	amplitude_hat,amplitude_for, amplitude_back = [],[],[]

	#-Hat type
	cond = True
	for jj,vmin in enumerate(ids_down): # hat type
		rest = (vmin - ids_up)
		rest_min = (vmin - ids_down)

		if len(rest[rest>0]) != 0:
			sel = rest == rest[rest>0].min()
			idvmax_aux = ids_up[sel][0]
			if len(rest_min[rest_min >0]) !=0:
				cond = rest_min[rest_min >0].min() >= (vmin - idvmax_aux)
			if cond:
				idhat.append([idvmax_aux+1,vmin])
				idhat_start.append(idvmax_aux+1)
				idhat_end.append(vmin)
				time_hat.append(vtime[[idvmax_aux+1,vmin]].value)
				amplitude_hat.append(vtime[[idvmax_aux+1,vmin]].value-vtime[[idvmax_aux,vmin+1]].value)
	if len(idhat) > 0:
		duration_hat = vtime[idhat_end] - vtime[idhat_start]
		time_hat = Time(time_hat,scale='utc',format='mjd')
		amplitude_hat = TimeDelta(amplitude_hat,scale='tai',format='jd')

	#-Forward type
	idauxf = [ii-1 for ii in idhat_start] # 
	idfor = sorted(list( set(ids_up).difference(idauxf)))

	time_for = vtime[idfor]
	if len(idfor) > 0:
		amplitude_for = vtime[np.array(idfor)+1] - vtime[idfor]

	#-Backward type
	idback = sorted(list( set(ids_down).difference(idhat_end) ))
	time_back = vtime[idback]
	if len(idback) > 0:
		amplitude_back = vtime[idback] - vtime[np.array(idback)+1]

	# showing
	if silent is not True:
		print('\n --> Time jumps and downs detected (indices):')
		print('\n jumps:',len(ids_up),'\n downs:',(ids_down))
		print('\n  Type: \n a) Hat indices:',idhat,
			  '\n b) Forward indices:',idfor,
			  '\n c) Backward indices:',idback)

	#Saving report
	report={'jumps':len(ids_up),'jumps_index':ids_up,'jumps_time':vtime[ids_up],
	        'downs':len(ids_down),'downs_index':ids_down,'downs_time':vtime[ids_down],
	        'delta_median':TimeDelta(vmedian,scale='tai',format='jd'),
	        'delta_ref':TimeDelta(dd_ref,scale='tai',format='jd'),
	        'hat':len(idhat),'hat_index':idhat,'hat_time':time_hat,
			'hat_index_start':idhat_start,'hat_index_end':idhat_end,
			'hat_amplitude':amplitude_hat,'hat_duration':duration_hat,
	        'forward':len(idfor),'forward_index':idfor,'forward_time':time_for,
			'forward_amplitude':amplitude_for,
	        'backward':len(idback),'backward_index':idback,'backward_time':time_back,
			'backward_amplitude':amplitude_back}
	return report


def get_statistic(vtime,report,idfigout=None):
	"""
	For one polarimeter, this function compares the time position of hats,
	forwards and backwards to obtain the time separation for each type case.

	--Parameter
	vtime  : time string (astropy.time.Time object as obtained from DataFile).

	report : dictionary of one polarimeter (in format of lookfor_timevariation
		ouput), which includes the hat, forward and backward indices.

	idfigout : string with the identification name to be used. If a string name
		is input the function plot the separation time for each type jump
		(two methods).

	--Return
	rep_out : dictionary with time separation of each hat/forward/backward
	using two approches:
	*) time comparison between two consecutive hat/forward/backward
	(named '_separation_').
	*) time comparison with respect to the first hat/forward/backward
	(named '_separationrel_').
	
	Also, this contains the indices used (i.e., 'hat_separationrel_index')
	"""
	rep_out = dict()

	jump_type =['hat','forward','backward']
	keys = ['_separation_index','_separationrel_index','_separation_time','_separationrel_time']
	rep_out = { k1+k2: [] for k1 in jump_type for k2 in keys}

	#Hat, Forward and backward cases
	for jtype in jump_type:
		if report[jtype] > 1:
			if jtype == 'hat':
				xind = [ii-1 for ii in report['hat_index_start']]
			else:
				xind = report[jtype+'_index']
			xtime = vtime[xind]
			#
			rep_out[jtype+'_separation_index'] = np.array(xind[1:])-np.array(xind[0:-1])
			rep_out[jtype+'_separationrel_index'] = np.array(xind[1:] - xind[0])
			rep_out[jtype+'_separation_time'] = xtime[1:] - xtime[0:-1]
			rep_out[jtype+'_separationrel_time'] = xtime[1:] - xtime[0]
			#
			if idfigout is not None:
				plt.figure(figsize=(6.4, 4.8))
				plt.xlabel(jtype); plt.ylabel('Time (sec)')
				plt.plot(rep_out[jtype+'_separationrel_time'].sec,'p--',mec='k',
					label='Separation (respect to the 1st)')
				plt.plot(rep_out[jtype+'_separation_time'].sec,'p--',mec='k',
					label='Separation')
				plt.legend(frameon=False)
				plt.savefig('Fig_'+idfigout+'_'+jtype+'.png',dpi=400,bbox_inches='tight')
				plt.close()
	return rep_out


##
# Main class to analyse the sci time string
##
class timevariation:

	def __init__(self, file,picklein=None):
		self.file = file
		self.data = h5py.File(file,'r')
		self.dfile = DataFile(file)
		#
		if picklein:
			print('\n --> Loading self.scitime from the pickle file \n')
			self.scitime = pickle.load(open(picklein,'rb'))
		else:
			print('\n --> Getting the self.scitime \n')
			self.scitime = self.query_timevariation(silent=True)
		self.scitime = {**self.scitime}


	def savePickle(self,filename):
		"""
		This function saves, in a pickle file, the dictionary
		with the sci time analysis.

		--Note: This function saves self.scitime.

		--Parameters
		filename : string file name.
		"""
		ff = open(filename,'wb')
		pickle.dump(self.scitime,ff)
		ff.close()


	def query_timevariation(self,tile=None,silent=True,data_type='PWR'):
		"""
		This function carry out the sci time variation analysis.

		--Notes: This computes self.scitime

		--Parameters
		tile  : string with the tile to be analyzed (by default
		all tiles are studied)
	
		--Return
		report_changes: ditionary with sci time analysis, whose
		keys identify the polarimeter, e.g.:
		    report_changes['POL_R0'].

			For each, a dictionary saves the numbers of 'jumps'
			and 'downs' in sci time, and the features clasified
			as 'hat', 'forwards' and 'backwards'. Note that the
			indices and times are sorted in '_index' and '_time'
			keys. In hat case, the start and end indices
			(or time) are saved as list (e.g. [index0,index2]).
			Also the reference delta time ('delta_ref') is saved.
		"""
		if tile is not None:
			pol = [pp  for pp in polarimeterXY if 'POL_'+tile in pp]
		else:
			pol = polarimeterXY
		report = {}	

		for pp in pol:
			print(' Case :',pp)
			time0, dataX0 = self.dfile.load_sci(pp,data_type)
			report[pp] = lookfor_timevariation(time0,step_ref=1.5,silent=True)
		self.scitime = {**report}
		return report


	def plot_timestatus(self,idcase='plot_sciTimeStatus',select=None,data_type='PWR'):
		"""
		This function plots and saves the sci time status of all
		polarimeter sorted in self.scitime(). This plot the time
		status, hat, forward and backward for all polarimeters or
		a subsection using the select option. 

		--Parameters
		idcase : string with the identification name to be used
			(default: "plot_sciTimeStatus").

		select : list with the polarimeter names to be plotted,
		e.g. ['R0', 'B1']. The number of polarimeter is also
		supported, e.g. ['0','3']
		"""
		kcases = [kk for kk in self.scitime]
		
		if select is not None:
			aux = []
			for ss in select:
				aux.extend([kk for kk in kcases if ss in kk[-2:]])
			kcases = aux
			print('\n--> Selection:',kcases)

		for kk in kcases:
			print('\n --> Plotting '+kk)
			report = self.scitime[kk]
			time0, pwrX0 = self.dfile.load_sci(kk,data_type)
			tt = time0.value
			xx = np.arange(len(tt))

			## Time status
			plt.figure(figsize=(6.4, 4.8))
			plt.title('Polarimeter '+kk.split('_')[1])
			plt.xlabel('Time step'); plt.ylabel('Time [mjd]')
			#
			if report['jumps'] > 0:
				for xjump in report['jumps_index']:
					plt.axvline(x=xjump,ls='--',color='k',alpha=0.6)
			if report['downs'] > 0:
				for xdown in report['downs_index']:
					plt.axvline(x=xdown+1,ls=':',color='C3',alpha=0.6)
			empty_patch1 = mpatches.Patch(color='none', label='Number of time jumps:'+str(report['jumps']))
			empty_patch2 = mpatches.Patch(color='none', label='Number of time downs:'+str(report['downs']))
			#
			plt.legend(handles=[empty_patch1,empty_patch2],frameon=False)
			plt.plot(xx,tt,'.-',color='C1',alpha=0.7)
			plt.savefig('Fig_'+idcase+'_polarimeter'+kk.split('_')[1]+'_time.png',dpi=400,bbox_inches='tight')
			plt.close()

			## Type: Hats, Forwards and /or backwards
			for jtype in ['hat','forward','backward']:
				njtype = report[jtype] # number of hats/forwards/backwards
				if njtype > 0:
					plt.figure(figsize=(6.4, 4.8*njtype))
					plt.title(jtype+' jumps')
					for ii,idref in enumerate(report[jtype+'_index']):
						if njtype !=1:
							plt.subplot(njtype,1,ii+1)
						if jtype == 'hat':
							nshift = int(0.1 * (idref[1]-idref[0]))
							tbefore = str(time0[idref[0]-1].datetime)
							tafter = str(time0[idref[0]].datetime)
							idref0 = [idref[0]-nshift,idref[1]+nshift]
						else:
							nshift = 20
							tbefore = str(time0[idref].datetime)
							tafter = str(time0[idref+1].datetime)
							idref0 = [idref-nshift,idref+nshift]
						#
						plt.plot(xx[idref0[0]:idref0[1]],tt[idref0[0]:idref0[1]],'--',alpha=0.8,color='C1',lw=1)
						plt.plot(xx[idref0[0]:idref0[1]],tt[idref0[0]:idref0[1]],'.',alpha=0.8,color='C0')
						plt.xlabel('Time step, polarimeter '+kk.split('_')[1])
						plt.ylabel('Time [mjd]')
						empty_patch0 = mpatches.Patch(color='none', label='Time Before: '+tbefore)
						empty_patch1 = mpatches.Patch(color='none', label='Time After : '+tafter)
						plt.legend(handles=[empty_patch0,empty_patch1],frameon=False)
					plt.savefig('Fig_'+idcase+'_polarimeter'+kk.split('_')[1]+'_time_'+jtype+'jumps.png',dpi=400,bbox_inches='tight')
					plt.close()


	def counting(self,idname='NumberCount_statistic',latex=False,csv=False,
		silent=False):
		"""
		This function counts the number of jumps and downs and
		the hat, forward and backward jumps type.

		--Parameters
		idname : string with the identification name to be used
			(default: "plotStatusparam").

		latex : If True the number count is saved in the table
		latex format (default: True). 

		csv   : If True the number count is saved in the CSV
		format (default: True). 

		--Return
		count : list with the number count of jumps and downs and
		the hat, forward and backward jumps type.
		"""
		count = [('Polarimeter','Jumps','Downs','Hats','Forwards','Backwards')]
		for kk in self.scitime.keys():
			rep = self.scitime[kk]
			cc = (kk.split('_')[1],rep['jumps'], rep['downs'], rep['hat'],rep['forward'],rep['backward'])
			count.append(cc)
		#
		if silent is False:
			print('\n Number of jumps:')
			for cc in count:
				print(cc[:])
		#
		if latex:
			print('\n--> saving in latex format')
			np.savetxt(idname+'_latex.txt', count, delimiter=' & ',fmt='%s', newline=' \\\\\n')
		if csv:
			print('--> saving in csv format')
			np.savetxt(idname+'.csv',count, delimiter=',',fmt='%s')
		return count


	def grouping(self,idname='NumberCount_group',latex=True,csv=True,
		silent=False):
		"""
		This function groups the polarimeter according to the
		number of jumps, downs, hats, forwards and backwards.

		--Parameters
		idname : string with the identification name to be used
			(default: "plotStatusparam").

		latex : If True the number count is saved in the table
		latex format (default: True). 

		csv   : If True the number count is saved in the CSV
		format (default: True). 

		--Returns
		group : list with the polarimeter grouped by number of jumps
		downs, hats, forwards and backwards
		"""
		count = self.counting(self,latex=False,csv=False,silent=True)[1:]
		newc = np.array([[cc[0],'{} {} {} {} {}'.format(cc[1],cc[2],cc[3],cc[4],cc[5])] for cc in count]) 
		group = [[ii,newc[newc[:,1]==ii,0]] for ii in np.unique(newc[:,1])]
		#
		if silent is False:
			print('\n Grouped by number of jumps, downs, hats, forwards and backwards:')
			for gg in group:
				print(gg[0]+'  :',gg[1])
		#
		if latex:
			print('\n--> saving in latex format')
			np.savetxt(idname+'_latex.txt',group, delimiter=' & ',fmt='%s', newline=' \\\\\n')
		if csv:
			print('--> saving in csv format')
			np.savetxt(idname+'.csv',group, delimiter=',',fmt='%s')
		return group


	def timeseparation(self,silent=False,idname=None):
		"""
		This function compares the time position of hat, forward and backward
		to obtain the time separation in each type case.

		Note: This function updates the self.scitime adding new keys with
		the time separation of each hat/forward/backward using two approches:
		*) time comparison between to consecutive time step
			(named '_separation_').
		*) time copmarison with respecto to the firsttime step
			(named '_separationrel_').
		Also, this includes the indices used (i.e., 'hat_separation_index')

		
		--Parameter
		idname  : string with the identification name to be used. If a string name
		is input the function plot the separation time (two methods).

		silent  : True by default

		--Return
		rep_out : dictionary with time separation of each hat/forward/backward
		using the two approches and indices used.
		"""
		for kk in self.scitime.keys():
			time0, _ =self.dfile.load_sci(kk,'PWR')
			rr = self.scitime[kk]
			#
			if idname is not None:
				rout = get_statistic(time0,rr,idname+'_'+kk)
			else: 
				rout = get_statistic(time0,rr)
			#
			print('--> self.scitime is updated')
			self.scitime[kk].update(rout)
			#
			if silent is not True:
				print('\n ## Polarimeter '+kk)
				for jtype in ['hat','forward','backward']:
					print('\n {} \n Met1: {} \n Met2: {}'.format(jtype,
						rout[jtype+'_separation_time'],
						rout[jtype+'_separationrel_time']))
			#


		
