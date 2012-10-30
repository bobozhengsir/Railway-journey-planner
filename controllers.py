#!/usr/bin/env python
#-*- coding: utf-8 -*-
import mimetypes
import cStringIO as StringIO
import sys
from bottle import request, response, get, post, route, Bottle, error
from bottle import static_file, redirect, HTTPResponse
from bottle import mako_view as view, mako_template as template
from PIL import Image
from models import Stop_time, Station, Stop_edges, Train, Direct_Plan, Tranfer_One_Plan, Plans
import json
from operator import itemgetter, attrgetter
import memcache
from hashlib import md5

MC = memcache.Client(['127.0.0.1:11211'],debug=0)


def connect_trains(sta_name, type_time):
	""" key function about the programm time
	type_time:
		start_station:"depart_time" ,start_station:"arrive_time" (==>None)
	"""
	if not isinstance(sta_name, unicode):
		sta_name = unicode(sta_name,'utf-8') 
	all_trains = {}
	for post in Stop_time.objects(__raw__={"sta_name":sta_name,type_time:{'$ne':None}}).only("seq_no","train_no"):
		all_trains[post.train_no] = post.seq_no #next can plus infomations

	return all_trains

def save_direct_trains(start_trains, end_trains):
	"""save direct edges
	"""
	direct_plans = []
	if len(start_trains) <= len(end_trains):
		for (k,v) in start_trains.items():
			if k in end_trains and v < end_trains[k]: #direct
				k_train = Train.objects(train_no=k).get()
				direct_plan = Direct_Plan(v, end_trains[k], k_train)
				direct_plans.append(direct_plan)
			
			
	else:
		for (k,v) in end_trains.items():
			if k in start_trains and v > start_trains[k]: #direct
				k_train = Train.objects(train_no=k).get()
				direct_plan = Direct_Plan(start_trains[k], v, k_train)
				direct_plans.append(direct_plan)
			
			
	#if direct_plans:
	return direct_plans

def connect_time(start_arrive_time,end_depart_time):
	"""return connection minutes at one station"""
	if int(start_arrive_time) < int(end_depart_time):
		return int(end_depart_time)/100*60 + int(end_depart_time)%100 - int(start_arrive_time)/100*60 - int(start_arrive_time)%100
	else:
		return 1440 + int(end_depart_time)/100*60 + int(end_depart_time)%100 - int(start_arrive_time)/100*60 - int(start_arrive_time)%100


def save_direct_plans(start_sta, end_sta):
	"""
	type_time:
		start_station:"depart_time" ,start_station:"arrive_time" (==>None)
	# be care: start_sta != end_sta (before ensure)
	"""
	try:
		start_trains = connect_trains(start_sta, "depart_time") #db one
		end_trains = connect_trains(end_sta, "arrive_time") #db two
		
		direct_plans = save_direct_trains(start_trains, end_trains)
	except Exception, e:
		raise e

	return direct_plans,start_trains,end_trains
	

def save_tranfer_one_plans(start_trains, end_trains):
	"""save one tranfer plans """
	tranfer_one_plans = [] #save tranfer result

	trains = lambda train:[(t,train[t.train_no]) for t in Train.objects(__raw__={"train_no":{"$in":train.keys()}})]

	start_train_seqs = trains(start_trains)
	start_sta_info =lambda d: dict([(s.sta_name, s) for s in d[0].edges if s.seq_no > d[1]]) #s.arrive_time,s.city_same
	start_trains_stas_v = map(start_sta_info, start_train_seqs)

	end_train_seqs = trains(end_trains)
	end_sta_info =lambda d: dict([(s.sta_name, s) for s in d[0].edges if s.seq_no < d[1]])#s.depart_time,s.city_same
	end_trains_stas_ev = map(end_sta_info, end_train_seqs)
		
	for i,sl in enumerate(start_trains_stas_v):
		set_one = set(sl.keys())
		train_one = start_train_seqs[i]
		for j,el in enumerate(end_trains_stas_ev):
			train_two = end_train_seqs[j]
			if len(train_one[0].cross_bureaus) == 1 and len(train_two[0].cross_bureaus) == 1:
				break #tranfer is not taking place in two bureau trains
			set_two = set(el.keys())
			set_union = set_one & set_two
			same_city_sta = [(st1,st2) for st1 in set_one - set_union for st2 in set_two - set_union \
							if sl[st1].city_same and sl[st1].city_same==el[st2].city_same]
			
			union_sets_sta = []
			union_sets_sta = list(set_union)
			union_sets_sta.extend(same_city_sta)

			if union_sets_sta:
				try:
					#union_sets_sta_dict = [] 
					#union_sets_sta_dict = zip(union_sets_sta, union_sets_sta)
					#union_sets_sta_dict.extend(same_city_sta)
					union_sets_connct_time = []
					union_sets_connct_time = [connect_time(sl[t].arrive_time, el[t].depart_time) for t in set_union]
					union_sets_connct_time.extend([connect_time(sl[t1].arrive_time, el[t2].depart_time) for (t1,t2) in same_city_sta])
				except TypeError, e:
					print "type error"
				except Exception, ex:
					print "other error"
					
				#union_sets_all = dict(zip(union_sets_sta,union_sets_connct_time))
				#union_sets_filter = sorted(union_sets_all.items(), key=lambda x: x[1])
				transit_time = max(union_sets_connct_time)
				for i,x in enumerate(union_sets_connct_time):
					if x==transit_time and i<len(set_union):
						transit_sta = union_sets_sta[i]
						transit_sta_seqs = (sl[transit_sta].seq_no, el[transit_sta].seq_no)
						tranfer_one = Tranfer_One_Plan(train_one[0],train_one[1], train_two[0],train_two[1], transit_sta_seqs, transit_sta,transit_time)
						tranfer_one_plans.append(tranfer_one)
						break
					elif x==transit_time and i>=len(set_union):
						if_city_same = True
						transit_stas = union_sets_sta[i]
						transit_sta_seqs = (sl[transit_stas[0]].seq_no, el[transit_stas[1]].seq_no)
						tranfer_one = Tranfer_One_Plan(train_one[0],train_one[1], train_two[0],train_two[1], transit_sta_seqs, transit_stas,transit_time,if_city_same)
						tranfer_one_plans.append(tranfer_one)
						break
					else:
						continue
				

	return tranfer_one_plans#,start_trains,end_trains


		


# route
webapp = Bottle()

@webapp.error(404)
def error404(error):
    return 'Nothing here, sorry'

@webapp.route('/')
@webapp.route('/hello/<name>')
def hello(name="world"):
	return "hello %s" % name

@webapp.route('/train/<train_code>',method="GET")
def gettrain(train_code):
	#mc_key = md5("stations")
	#stations = MC.get(mc_key) 
	train_code = str.upper(train_code)
	train = Train.objects(__raw__={'board_train_code':{'$all':[train_code,]}}).get()
	if 'callback' in request.query:
		callback = request.query.callback
		response.content_type = 'application/javascript'
		return callback + '(' + train.to_json() + ');'
	else:
		response.content_type = 'application/json'
		return json.dumps(train.to_dict(), indent=4) 


@webapp.route('/stations')
def stations():
	response.content_type = 'application/json'
	#mc_key = md5("stations")
	#stations = MC.get(mc_key) 
	stations = Station.objects()
	return json.dumps([s.to_dict() for s in stations],indent=4)

@webapp.get('/search')
def search_form():
	return """<form method="GET" action="/result">
					<input name="start_sta" type="text" />
					<input name="end_sta" type="text" />
					<input name="submit" type="submit" />
				</form>"""

#provide json implement
@webapp.route('/result/<start_sta>/<end_sta>/<preference>', method='GET')
def search_submit(start_sta, end_sta, preference):
	#start_sta	 = request.query.start_sta
	#end_sta		 = request.query.end_sta
	results, start_trains, end_trains = save_direct_plans(start_sta, end_sta)

	if not results:
		results = save_tranfer_one_plans(start_trains, end_trains)
	if preference == "travel_time":
		result = sorted(results, key=attrgetter('travel_time', 'distance'))
	else:
		result = sorted(results, key=attrgetter('distance', 'travel_time'))
	plans = Plans(start_sta, end_sta,edges=result[:5])

	if 'callback' in request.query:
		callback = request.query.callback
		response.content_type = 'application/javascript'
		return callback + '(' + plans.to_json() + ');'
	else:
		response.content_type = 'application/json'
		return json.dumps(plans.to_dict(), indent=4) 


if __name__ == '__main__':
	import time
	import sys
	start_sta = raw_input("start station:")
	end_sta = raw_input("end station:")
	start_time = time.time()
	results,start_trains,end_trains = save_direct_plans(start_sta, end_sta)
	if not results:
		results = save_tranfer_one_plans(start_trains, end_trains)
	result = sorted(results, key=attrgetter('travel_time','distance'))
	plans = Plans(start_sta, end_sta,edges=result[:1])
	
	elapsed = time.time() - start_time

	print elapsed
	print plans.to_json()

	



