# -*- coding: utf-8 -*-
"""
Created on Sun Oct  9 12:14:14 2022

@author: Marc
"""

import sys
sys.path.insert(1, '../utils/')

import time
inicio = time.time()
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from Main_Algoritmo_ViterbiForzado_DNN import Algoritmo_Viterbi_Forzado
from torch.utils.data import DataLoader, Dataset, random_split, TensorDataset

from sklearn import metrics
import matplotlib.pyplot as plt
import numpy as np
import IPython
import pandas as pd

import copy
import random
import time



SEED = 42

random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
torch.cuda.manual_seed(SEED)
torch.backends.cudnn.deterministic = True


database_test = 'Val' # Selección de la base de datos a testear. Puede ser Test, Val o Train
name_database_train = 'NorthChile' # Nombre de la base de datos con la que se quiere entrenar
name_database_test =  'NorthChile' # Nombre de la base de datos con la que se quiere testear

path_probPrior_train = '../../data/'+name_database_train+'/features/Probs_Prior_'+name_database_train+'_Train.npy'

path_modelo = '../../models/model_MLP_HMM_'+name_database_train+'.pt'

ref_file_test = '../../data/'+name_database_test+'/reference/Referencia_'+name_database_test+'_'+database_test +'xlsx'

path_feat_test = '../../data/'+name_database_test+'/features/Features_'+name_database_test+'_'+database_test +'.npy'   

probPriorTrain  = np.load(path_probPrior_train, allow_pickle=True)  
  
#Se define el modelo
class MLP(nn.Module):
    def __init__(self, input_dim, output_dim):
        super().__init__()
        self.input_fc = nn.Linear(input_dim, 24)
        self.hidden_fc1 = nn.Linear(24, 20)
        self.hidden_fc2 = nn.Linear(20, 16)
        self.hidden_fc3 = nn.Linear(16, 12)
        self.output_fc = nn.Linear(12, output_dim)

    def forward(self, x):
        # x = [batch size, height, width]
        batch_size = x.shape[0]
        x = x.view(batch_size, -1)
        h_0 = F.relu(self.input_fc(x))
        h_1 = F.relu(self.hidden_fc1(h_0))
        h_2 = F.relu(self.hidden_fc2(h_1))
        h_3 = F.relu(self.hidden_fc3(h_2))
        y_pred = self.output_fc(h_3)
        return y_pred, h_3

INPUT_DIM = 918  #Features con contexto
OUTPUT_DIM = 12  #Estados 

model = MLP(INPUT_DIM, OUTPUT_DIM)
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')


model.load_state_dict(torch.load(path_modelo))

def count_parameters(model):
    # Funcion que cuenta el número de parámetros
    return sum(p.numel() for p in model.parameters() if p.requires_grad)
print(f'The model has {count_parameters(model):,} trainable parameters')


def get_predictions(model, iterator, device):
    # Funcion que realiza la prediccion del modelo
    model.eval()
    images = []
    labels = []
    probs = []

    with torch.no_grad():
        for (x, y) in iterator:
            x = x.to(device)
            y_pred, _ = model(x.float())
            y_prob = F.softmax(y_pred, dim=-1)

            images.append(x.cpu())
            labels.append(y.cpu())
            probs.append(y_prob.cpu())

    images = torch.cat(images, dim=0)
    labels = torch.cat(labels, dim=0)
    probs = torch.cat(probs, dim=0)

    return images, labels, probs


def DNN2ProbObs(feat_entrada):
    """    
    Funcion que calcula las probabilidad de observacion a partir de lo obtenido por
    la DNN y las probabilidades a priori
    """
    salida_DNN = []
    for traza in feat_entrada:

        set_conjunto = TensorDataset(torch.from_numpy(traza),-1*torch.ones(len(traza))) #El target lo seteo en -1, da lo mismo
        conjunto_iterator = DataLoader(set_conjunto) 
        images, _ , probs = get_predictions(model, conjunto_iterator, device)
        salida_DNN.append(probs)

    calculo_Prob = []
    for ProbTraza in salida_DNN:
        calculo_Prob.append(np.log(ProbTraza)- np.log(probPriorTrain))

    Probs_Observations = []
    for traza in calculo_Prob:  
        ruido = traza[:,0:3]
        evento = traza[:,3:]
        Probs_Observations.append([np.array(ruido),np.array(evento)])
    return Probs_Observations


X_test = np.load(path_feat_test, allow_pickle = True)
Probs_Observations_test = DNN2ProbObs(X_test)


##################################### Algoritmo Viterbi #######################################3

file_viterbi_test = 'results/Viterbi_DNN_test'
phones="../../models/phones_3estados.txt"
transitions_file="../../models/final_16_layers3_s1_lr001_"+name_database_train+".mdl"


#test
# Se aplica el algoritmo de Viterbi sobre una base de datos
Algoritmo_Viterbi_Forzado( phones,transitions_file,Probs_Observations_test,database_test,name_database_test)
print(f'The model has {count_parameters(model):,} trainable parameters')

fin = time.time()
print(fin-inicio)



