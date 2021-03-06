# usage: python train.py {database_host} {model_filepath}
# e.g. python train.py 35.187.144.113 models/trained_model.pkl

import sys
import pandas as pd
import numpy as np
from utils import postgres_connector, load_df
from fastai.tabular import *
from fastai.callbacks import *
import os

def createDataLoader(df, cat_names, dep_var, path="model_path", sample_frac=0.1, dev_set_size=2000, procs=None):
	if not procs:
		procs = [FillMissing, Categorify, Normalize]
	valid_idx = range(len(df)-dev_set_size, len(df))
	data = TabularDataBunch.from_df(path, df, dep_var, valid_idx=valid_idx, procs=procs, cat_names=cat_names)
	return data

def train(dataLoader, layers, emb_szs, model_filepath, lr=5e-2,  num_epochs=20):
	f_score = FBeta(average='macro', beta=1)
	learn = tabular_learner(dataLoader, layers=layers, emb_szs=emb_szs, metrics=f_score)
	callbacks = [SaveModelCallback(learn, name='best'),
				 EarlyStoppingCallback(learn, min_delta=1e-5, patience=5),]
				 #ShowGraph(learn)]
	learn.callbacks = callbacks
	# The next 2 lines gave the starting lr of 5e-2
	# learn.lr_find()
	# learn.recorder.plot() 
	learn.fit_one_cycle(num_epochs, lr)
	return learn

if __name__ == "__main__":

	database_host, model_filepath = None, None
	if len(sys.argv) != 4:
		print('usage: python train.py {database_host} {model_filepath}')
		print('e.g. python train.py 35.187.144.113 models/trained_model.pkl')
	
	database_host = sys.argv[1]
	model_filepath = sys.argv[2]
	file_path = '/'.join(model_filepath.split('/')[:-1])
	file_name = model_filepath.split('/')[-1]
	try:
		os.mkdir(file_path)
	except OSError:
		print('Failed to create directory.')
	else:
		print('Succesfully created directory.')

	# Get connect engine   
	engine = postgres_connector(
	   database_host,
	   5432,
	   "intern_task",
	   "candidate",
	   "dcard-data-intern-2020"
	)
	df = load_df(engine, mode='train')
	df.drop('post_key', axis=1, inplace=True)
  	
	cat_names = ['created_at_dayofweek',  'created_at_hour']
	dep_var = 'is_trending'
	
	print('Creating data loader...')
	dataLoader = createDataLoader(df, cat_names, dep_var, file_path)
	print('Data loader created.')

	layers=[200,100]
	emb_szs={'created_at_Dayofweek': 10, 'created_at_Hour': 15}
	print('Using a {}-level MLP. Sizes are '.format(len(layers)) + str(layers))
	print('Embedding sizes:')
	print(emb_szs)
	print('Start training...')
	learn = train(dataLoader, layers, emb_szs, model_filepath, num_epochs=30)
	learn.export(file_name)
