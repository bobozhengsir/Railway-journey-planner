#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
from mongoengine import EmbeddedDocument, Document, connect
from mongoengine import StringField, IntField, FloatField, ListField, SortedListField, EmbeddedDocumentField
from mongoengine.queryset import (QuerySet, QuerySetManager,
                                  MultipleObjectsReturned, DoesNotExist,
                                  QueryFieldList)

from mongoengine.connection import ConnectionError

from json import dumps as json_dumps, loads as json_lds

DB_NAME = 'mytimetable'
PLAN_PROPERTY = {"Direct_Plan": 0, "Tranfer_One_Plan": 1, "Tranfer_Two_Plan": 2}

class Station(Document):
	"""docstring for Dic_station"""
	station_code 		= StringField(required=True)
	station_name		= StringField(required=True)
	station_shortcode	= StringField(required=True)
	bureau_code			= StringField(required=True)
	station_class		= StringField(required=True)
	city_code			= StringField(required=True)
	station_pycode		= StringField(required=True)
	province_code		= StringField(required=True)

	def to_dict(self):
		return {
    		"station_name": self.station_name,
		    "station_pycode": self.station_pycode,
		    "station_shortcode": self.station_shortcode,
		    "province_code": self.province_code,
		}

	def to_json(self):
		return json_dumps(self.to_dict(), indent=4)

	meta = {
        'collection': 'dic_station',
        'allow_inheritance': False,
	}

class Stop_time(Document):
	"""docstring for Stop_time"""
	train_no 			= StringField(required=True)
	seq_no 				= IntField(required=True)
	sta_name 			= StringField(required=True)
	board_train_code 	= StringField(required=True)
	depart_days 		= IntField(required=True)
	arrive_time 		= StringField(required=True)
	depart_time 		= StringField(required=True)
	distance 			= FloatField(required=True)

	meta = {
        'collection': 'stop_time',
        'allow_inheritance': False,
	}

class Stop_edges(EmbeddedDocument):
	"""docstring for Edges"""
	seq_no 				= IntField(required=True)
	sta_name 			= StringField(required=True)
	depart_days 		= IntField(required=True)
	arrive_time 		= StringField(required=True)
	depart_time 		= StringField(required=True)
	distance 			= IntField(required=True)
	city_same 			= StringField()# maybe is None

	def to_dict(self):
		return {
			"seq_no": self.seq_no,
			"sta_name": self.sta_name,
			"depart_days": self.depart_days,
			"arrive_time": self.arrive_time,
			"depart_time": self.depart_time,
			"distance": self.distance,
		}

	def to_json(self):
		return json_dumps(self.to_dict(), indent=4)

		
class Train(Document):
	"""docstring for Dic_train"""
	train_no 			= StringField(required=True, unique=True)
	board_train_code 	= ListField(StringField())
	start_time 			= StringField(required=True)
	end_time 			= StringField(required=True)
	depart_days 		= IntField(required=True)
	ori_sta_tele_code 	= StringField(required=True)
	ori_sta_name 		= StringField(required=True)
	dest_sta_tele_code 	= StringField(required=True)
	dest_sta_name 		= StringField(required=True)
	edges_no 			= IntField(required=True)
	distance 			= IntField(required=True)
	cross_bureaus 		= ListField(StringField())
	edges 				= SortedListField(EmbeddedDocumentField(Stop_edges), ordering="seq_no")

	

	meta = {
        'collection': 'dic_train',
        'allow_inheritance': False,
	}

	def to_dict(self):
		return {
    		"train_no": self.train_no,
    		"board_train_code": "/".join(list(self.board_train_code)),
    		"start_time": self.start_time,
    		"end_time": self.end_time,
    		"depart_days": self.depart_days,
    		"ori_sta_name": self.ori_sta_name,
    		"dest_sta_name": self.dest_sta_name,
    		"edges_no": self.edges_no,
    		"distance": self.distance,
    		"edges": [e.to_dict() for e in self.edges]

		}

	def to_json(self):
		return json_dumps(self.to_dict(), indent=4)
    	



class Direct_Plan(object):
	"""docstring for Direct_Plan"""
	def __init__(self, ori_sta_seq, dest_sta_seq, train):
		#super(Direct_Plan, self).__init__()
		
		self.ori_sta_seq = ori_sta_seq
		self.dest_sta_seq = dest_sta_seq
		self.train = train#Train.objects(train_no=train_num).get()

		self.start_station_name = self.train.edges[ori_sta_seq - 1].sta_name
		self.end_station_name = self.train.edges[dest_sta_seq - 1].sta_name

		self.start_time = self.__getStartTime()
		self.end_time = self.__getEndTime()
		self.depart_days = self.__getDepartDays()
		self.distance = self.__getDistance()
		self.travel_time = self.__count_time()


	def __getStartTime(self):
		return self.train.edges[self.ori_sta_seq - 1].depart_time
	def __getEndTime(self):
		return self.train.edges[self.dest_sta_seq - 1].arrive_time
	def __getDepartDays(self):
		return self.train.edges[self.dest_sta_seq - 1].depart_days - self.train.edges[self.ori_sta_seq - 1].depart_days
	def __getDistance(self):
		return self.train.edges[self.dest_sta_seq - 1].distance - self.train.edges[self.ori_sta_seq - 1].distance
	def __count_time(self):
		#depart_days = self.train.edges[self.dest_sta_seq - 1].depart_days - self.train.edges[self.ori_sta_seq - 1].depart_days
		count_mins = self.depart_days * 1440 + int(self.end_time)/100*60 + int(self.end_time)%100 - int(self.start_time)/100*60 - int(self.start_time)%100
		return count_mins

	def to_dict(self):
		return {
			"start_time": self.start_time,
			"end_time": self.end_time,
			"start_station_name": self.start_station_name,
			#"start_station_code": ,
			"end_station_name": self.end_station_name,
			#"end_station_code": ,
			"price": 0,#it has no price now.
			"travel_time": self.travel_time,
			"distance": self.distance,
			"comfort": "null",#it sets null default,it has no data.
			"train_no": self.train.train_no,
			"board_train_code": "/".join(list(self.train.board_train_code)),
			"ori_sta_seq": self.ori_sta_seq,
			"dest_sta_seq": self.dest_sta_seq,
			"plan_property": PLAN_PROPERTY["Direct_Plan"],
		}

	def to_json(self):
		return json_dumps(self.to_dict(), indent=4)


class Tranfer_One_Plan(object):
	"""docstring for Tranfer_One_Plan"""
	def __init__(self,first_train, ori_sta_seq, second_train, dest_sta_seq, transit_sta_seqs,transit_stas, transit_time, if_city_same=False):
		#super(Tranfer_One_Plan, self).__init__()
		#self.dest_sta_name = dest_sta_name
		self.if_city_same = if_city_same #if it is True,transit_sta is tuple(a,b).if it's false,transit_sta is one sta.
		self.transit_time = transit_time
		self.first_direct = Direct_Plan(ori_sta_seq, transit_sta_seqs[0], first_train)
		self.second_direct = Direct_Plan(transit_sta_seqs[1], dest_sta_seq, second_train)
		self.transit_sta = transit_stas #same city has two transit_sta
		self.distance = self.first_direct.distance + self.second_direct.distance
		self.start_time = self.first_direct.start_time
		self.end_time = self.second_direct.end_time
		self.travel_time = self.first_direct.travel_time + self.second_direct.travel_time + transit_time

	def to_dict(self):
		return {
			"start_time": self.start_time,
			"end_time": self.end_time,
			"start_station_name": self.first_direct.start_station_name,
			#"start_station_code": "BBH",
			"end_station_name": self.second_direct.end_station_name,
			#"end_station_code": "AFW",
			"price": 0,
			"travel_time": self.travel_time,
			"distance": self.distance,
			"comfort": "null",
			"if_city_same": self.if_city_same,
			"transit_sta": self.transit_sta,
			"transit_time": self.transit_time,
			"plan_property": PLAN_PROPERTY["Tranfer_One_Plan"],
			"edges": [self.first_direct.to_dict(), self.second_direct.to_dict()],
				       
		}
			
	def to_json(self):
		return json_dumps(self.to_dict(), indent=4)

class Tranfer_Two_Plan(object):
	"""docstring for Tranfer_Two_Plan"""
	def __init__(self,first_train, ori_sta_seq, second_train, dest_sta_seq, transit_sta_seqs,transit_stas, transit_time, if_city_same=False):
		#super(Tranfer_One_Plan, self).__init__()
		#self.dest_sta_name = dest_sta_name
		self.if_city_same = if_city_same #if it is True,transit_sta is tuple(a,b).if it's false,transit_sta is one sta.
		self.transit_time = transit_time
		self.first_direct = Direct_Plan(ori_sta_seq, transit_sta_seqs[0], first_train)
		self.second_direct = Direct_Plan(transit_sta_seqs[1], dest_sta_seq, second_train)
		self.transit_sta = transit_stas #same city has two transit_sta
		self.distance = self.first_direct.distance + self.second_direct.distance
		self.start_time = self.first_direct.start_time
		self.end_time = self.second_direct.end_time
		self.travel_time = self.first_direct.travel_time + self.second_direct.travel_time + transit_time

	def to_dict(self):
		return {
			"start_time": self.start_time,
			"end_time": self.end_time,
			"start_station_name": self.first_direct.start_station_name,
			#"start_station_code": "BBH",
			"end_station_name": self.second_direct.end_station_name,
			#"end_station_code": "AFW",
			"price": 0,
			"travel_time": self.travel_time,
			"distance": self.distance,
			"comfort": "null",
			"if_city_same": self.if_city_same,
			"transit_sta": self.transit_sta,
			"transit_time": self.transit_time,
			"plan_property": PLAN_PROPERTY["Tranfer_One_Plan"],
			"edges": [self.first_direct.to_dict(), self.second_direct.to_dict()],
				       
		}
			
	def to_json(self):
		return json_dumps(self.to_dict(), indent=4)

class Plans(object):
	"""all Plans between OD"""
	def __init__(self, start_sta, end_sta, edges=[]):
		self.start_sta = start_sta
		self.end_sta   = end_sta
		self.edges = edges

	def __add__(self, plan):
		"""plan maybe is Direct_Plan or Tranfer_One_Plan,etc"""
		self.edges.extend(plan)

	def __nonzero__(self):
		"""use when if Plans"""
		return bool(self.edges)

	def to_dict(self):
		return {
			"start_station_name": self.start_sta,
			"end_station_name": self.end_sta,
			"edges": [e.to_dict() for e in self.edges]
		}

	def to_json(self):
		return json_dumps(self.to_dict(), indent=4)
		
		
try:
	connect(DB_NAME)
except ConnectionError: 
	print "Cannot connect to the database"
	sys.exit(1)
 