#! /usr/bin/env python
#-*- coding: utf-8 -*-

def connect_time(start_arrive_time,end_depart_time):
	"""return connection minutes at one station"""
	if int(start_arrive_time) < int(end_depart_time):
		return int(end_depart_time)/100*60 + int(end_depart_time)%100 - int(start_arrive_time)/100*60 - int(start_arrive_time)%100
	else:
		return 1440 + int(end_depart_time)/100*60 + int(end_depart_time)%100 - int(start_arrive_time)/100*60 - int(start_arrive_time)%100
