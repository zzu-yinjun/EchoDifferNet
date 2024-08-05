# -*- coding: utf-8 -*-
"""functions.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1Jip3Ax3dTfyqTgG8w2THZL_IRF7ziZPS
"""

import torch
import cv2
import os
import numpy as np
import shutil

# from google.colab.patches import cv2_imshow
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
import math
from PIL import Image
import torch.nn as nn
import yaml
import random

import matplotlib.pyplot as plt

# from google.colab import files
import sys
import time
from torch.utils.data import random_split

# from Model.Data_Process.data_processing import *
# from Model.Model1.model1_script import *


def deb(param, str):
    print(str + " = {}".format(param))


def load_config(file_path):
    with open(file_path, "r") as file:
        config = yaml.safe_load(file)
    return config


def count_params(model):
    sum = 0
    for param in model.parameters():
        sum = sum + param.numel()
    return sum


"""
def find_next_file(first, second):
  first_list = sorted(os.listdir(first))
  second_list = sorted(os.listdir(second))
  length = len(first_list)
  while True:
    rand_int = random.randint(0, length - 1)
    target = first_list[rand_int]
    if target in second_list:
      return first + '/' + target, second + '/' + target
"""


def sigmoid(x):
    return 1 / (np.exp(-x) + 1)


def get_beta_schedule(beta_schedule, *, beta_start, beta_end, num_diffusion_timesteps):

    if beta_schedule == "quad":
        betas = (
            np.linspace(
                beta_start**0.5,
                beta_end**0.5,
                num_diffusion_timesteps,
                dtype=np.float64,
            )
            ** 2
        )
    elif beta_schedule == "linear":
        betas = np.linspace(
            beta_start, beta_end, num_diffusion_timesteps, dtype=np.float64
        )
    elif beta_schedule == "const":
        betas = beta_end * np.ones(num_diffusion_timesteps, dtype=np.float64)
    elif beta_schedule == "jsd":  # 1/T, 1/(T-1), 1/(T-2), ..., 1
        betas = 1.0 / np.linspace(
            num_diffusion_timesteps, 1, num_diffusion_timesteps, dtype=np.float64
        )
    elif beta_schedule == "sigmoid":
        betas = np.linspace(-6, 6, num_diffusion_timesteps)
        betas = sigmoid(betas) * (beta_end - beta_start) + beta_start
    else:
        raise NotImplementedError(beta_schedule)
    assert betas.shape == (num_diffusion_timesteps,)
    return betas


def compute_alpha(beta, t):  # t給tensor 一維的
    beta = torch.cat([torch.zeros(1).to(beta.device), beta], dim=0)
    a = (1 - beta).cumprod(dim=0).index_select(0, t + 1).view(-1, 1, 1, 1)
    return a


def get_timestep_embedding(timesteps, embedding_dim):

    assert len(timesteps.shape) == 1

    half_dim = embedding_dim // 2
    emb = math.log(10000) / (half_dim - 1)
    emb = torch.exp(torch.arange(half_dim, dtype=torch.float32) * -emb)
    emb = emb.to(device=timesteps.device)
    emb = timesteps.float()[:, None] * emb[None, :]
    emb = torch.cat([torch.sin(emb), torch.cos(emb)], dim=1)
    if embedding_dim % 2 == 1:  # zero pad
        emb = torch.nn.functional.pad(emb, (0, 1, 0, 0))
    return emb

def image_loader_to_tensor(tensor):
  tensor = tensor.to(torch.float32)
  tensor = tensor / 255.0
  tensor = tensor * 2.0
  tensor = tensor - 1.0
  tensor = tensor.permute(0, 3, 1, 2)
  return tensor

def spectrogram_loader_to_tensor(tensor, min_value, max_value):
    # Convert to float32
    tensor = tensor.to(torch.float32)
    
    # Normalize to range [0, 1]
    tensor = (tensor - min_value) / (max_value - min_value)
    
    # Scale to range [0, 2]
    tensor = tensor * 2.0
    
    # Shift to range [-1, 1]
    tensor = tensor - 1.0
    
    # Permute dimensions to (batch_size, channels, height, width)
 
    
    return tensor
# for the batch normalization
def Normalize(input, channels, momentum=0.1, epsilon=1e-5):
    bn = nn.BatchNorm2d(channels, momentum=momentum, eps=epsilon)
    return bn(input)


def nonlinearity(x):

    return x * torch.sigmoid(x)


def Normalize(in_channels):
    return torch.nn.GroupNorm(
        num_groups=32, num_channels=in_channels, eps=1e-6, affine=True
    )


def get_index_from_list(values, t, x_shape):
    batch_size = t.shape[0]
    """
    pick the values from vals
    according to the indices stored in `t`
    """
    result = values.gather(-1, t)
    """
    if
    x_shape = (5, 3, 64, 64)
        -> len(x_shape) = 4
        -> len(x_shape) - 1 = 3

    and thus we reshape `out` to dims
    (batch_size, 1, 1, 1)

    """
    return result.reshape(batch_size, *((1,) * (len(x_shape) - 1))).to(t.device)


"""
def training(start_epoch, steps, load_path, model, PRINT_FREQUENCY,  optimizer, save_frequency, trainloader, validloader, datasets_path, batch_size, config, device, weights_save_path, loss_save_path, gradient_save_path = None, save_gradient = False): # load path is where the already existed weights save
  initial = start_epoch

  NO_EPOCHS = steps # 要多做幾個epochs
  # load_path = '/content/drive/MyDrive/Colab Notebooks/共用區/Simple_DE/Checkpoint/weight_save/weight_{}.pth'.format(initial) # 位置要改
  checkpoint = torch.load(load_path)

  start = checkpoint['epoch'] + 1
  # model_state_dict = checkpoint['model_state_dict']

  model.load_state_dict(checkpoint['model_state_dict'])
  optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
  for epoch in range(start , start + NO_EPOCHS + 1):
      start_time = time.time()
      epoch_gradient = {}
      mean_epoch_loss = []
      mean_epoch_loss_val = []
      for batch in trainloader:
          t = torch.randint(0, config['diffusion']['num_diffusion_timesteps'], (batch_size,)).long().to(device)

          input_img = batch['img'].to(torch.float32).to(device)
          target_depth = batch['depth'].to(torch.float32).to(device)

          pred_depth = model(input_img, target_depth, t)

          optimizer.zero_grad()
          loss = torch.nn.functional.mse_loss(target_depth, pred_depth)
          mean_epoch_loss.append(loss.item())
          loss.backward()

          if save_gradient :
            for name, param in model.named_parameters():
              if name not in epoch_gradient:
                epoch_gradient[name] = param.grad.clone()
              else:
                epoch_gradient[name] += param.grad


          optimizer.step()

      with torch.inference_mode():
        for batch in validloader:
          t = torch.randint(0, config['diffusion']['num_diffusion_timesteps'], (batch_size,)).long().to(device)
          input_img = batch['img'].to(torch.float32).to(device)
          target_depth = batch['depth'].to(torch.float32).to(device)

          pred_depth = model(input_img, target_depth, t)

          val_loss = torch.nn.functional.mse_loss(target_depth, pred_depth)
          mean_epoch_loss_val.append(val_loss.item())

      if epoch % save_frequency == 0 or epoch == start + NO_EPOCHS:
          checkpoint = {
            'epoch': epoch,
            'model_state_dict': model.state_dict(), # model.state_dict()是存下param的的值和形狀
            'optimizer_state_dict': optimizer.state_dict(), # optimizer.state_dict()則是存下優化器的param如momentum等等 不包含當下梯度
            'valid_loss' : np.mean(mean_epoch_loss_val),
            'loss' : np.mean(mean_epoch_loss) # 記得不能存tensor
          }

          torch.save(checkpoint, 'weight_{}.pth'.format(epoch))
          source_path = 'weight_{}.pth'.format(epoch)
          destination_path = weights_save_path


          # save them to the google drive
          shutil.copy(source_path, destination_path)
          #---計算時間---vvv
          end_time = time.time()
          exe_time = end_time - start_time
          hours, remainder = divmod(execution_time, 3600)
          minutes, seconds = divmod(remainder, 60)
          #---計算時間---^^^
          #-----以下是存loss的---vvv
          checkpoint = {
            'epoch': epoch,
            'valid_loss' : np.mean(mean_epoch_loss_val),
            'loss' : np.mean(mean_epoch_loss), # 記得不能存tensor
            'time' : exe_time
          }

          torch.save(checkpoint, 'loss_{}.pth'.format(epoch))
          source_path = 'loss_{}.pth'.format(epoch)
          destination_path = loss_save_path
          #-----存gradient---vvv
          if save_gradient:
            checkpoint = {
            'gradients' : epoch_gradient
          }
          torch.save(checkpoint, 'gradient_{}.pth'.format(epoch))
          source_path = 'gradient_{}.pth'.format(epoch)
          destination_path = gradient_save_path
          shutil.copy(source_path, destination_path)

          #-----存gradient---^^^
          # save them to the google drive
          shutil.copy(source_path, destination_path)
          #-----以下是存loss的---^^^

        if epoch % PRINT_FREQUENCY == 0:
          print('---')
          print(f"Epoch: {epoch} | Train Loss {np.mean(mean_epoch_loss)} | Val Loss {np.mean(mean_epoch_loss_val)}")
          print("time = {}:{}:{}".format(hours, minutes, seconds))
"""


class Model_optimize:
    def __init__(self, model, weight_path, loaded=False, device="cuda"):
        if loaded == False:
            checkpoint = torch.load(weight_path, map_location=torch.device(device))
            model.load_state_dict(checkpoint["model_state_dict"])
        self.model = model
        count = 0
        for name, param in model.named_parameters():
            count += 1
        self.amount_of_param = count

    def find_a_parameter(self, target):
        list = []

        for name, param in model.named_parameters():
            par_shape = len(param.shape)
            if par_shape == 1:
                if param[0] == target:
                    list.append(name)
            elif par_shape == 2:
                if param[0][0] == target:
                    list.append(name)
            elif par_shape == 3:
                if param[0][0][0] == target:
                    list.append(name)
            elif par_shape == 4:
                if param[0][0][0][0] == target:
                    list.append(name)
        return list

    def analyst_param(self):
        for name, param in model.named_parameters():
            print("{} | {}".format(name, param))
            print("--------------------------")

    def list_name(self):
        for name, param in model.named_parameters():
            print(name)
            print("--------------------------")

    def statics(self):
        for name, param in model.named_parameters():
            print(
                "{} | max = {} | min = {} | mean = {}".format(
                    name, torch.max(param), torch.min(param), torch.mean(param)
                )
            )

    def plot_name(self, name):
        for names, param in model.named_parameters():
            if names == name:
                weights_list = param.data.cpu().numpy().flatten()
                plt.figure(figsize=(7, 5))
                plt.title("Weight Distribution")
                plt.hist(weights_list, bins=50, alpha=0.7)
                plt.xlabel("Weight Value")
                plt.ylabel("Frequency")
                plt.show()

                break

    def plot_idx(self, idx):
        count = 0
        for names, param in model.named_parameters():
            if count == idx:
                weights_list = param.data.cpu().numpy().flatten()
                plt.figure(figsize=(7, 5))
                plt.title(names)
                plt.hist(weights_list, bins=50, alpha=0.7)
                plt.xlabel("Weight Value")
                plt.ylabel("Frequency")
                plt.show()

                break
            count += 1

    def plot_whole_sep(self):
        for idx in range(self.amount_of_param):
            self.plot_idx(idx)

    def plot_whole(self):
        weights_list = []
        for name, param in model.named_parameters():
            weights_list.append(param.data.cpu().numpy().flatten())
        plt.figure(figsize=(7, 5))
        plt.title("whole_plot")
        plt.hist(weights_list, bins=50, alpha=0.7)
        plt.xlabel("Weight Value")
        plt.ylabel("Frequency")
        plt.show()


class Model_optimize_comp:
    def __init__(
        self, Model, config, weight_path1, weight_path2, loaded=False, device="cuda:0"
    ):
        if loaded == False:
            checkpoint = torch.load(weight_path1, map_location=torch.device(device))
            self.grad1 = checkpoint["gradients"]
            model = Model(config)
            model.load_state_dict(checkpoint["model_state_dict"])
            self.model1 = model
            del model
            model = Model(config)
            checkpoint = torch.load(weight_path2, map_location=torch.device(device))
            self.grad2 = checkpoint["gradients"]
            model.load_state_dict(checkpoint["model_state_dict"])
            self.model2 = model

        count = 0
        for name, param in self.model1.named_parameters():
            count += 1
        self.amount_of_param = count

    def list_name(self):
        for name, param in self.model1.named_parameters():
            print(name)
            print("--------------------------")

    def statics(self):
        for name, param in self.model1.named_parameters():
            for name2, param2 in self.model2.named_parameters():
                if name2 == name:
                    break
            print(
                "{} | max = {} | min = {} | mean = {}".format(
                    name, torch.max(param), torch.min(param), torch.mean(param)
                )
            )
            print(
                "{} | max = {} | min = {} | mean = {}".format(
                    name, torch.max(param2), torch.min(param2), torch.mean(param2)
                )
            )

    def plot_name(self, name):
        for names, param in self.model1.named_parameters():
            if names == name:
                weights_list = param.data.cpu().numpy().flatten()
                plt.figure(figsize=(7, 5))
                plt.title("Weight Distribution")
                plt.hist(weights_list, bins=50, alpha=0.7)
                plt.xlabel("Weight Value")
                plt.ylabel("Frequency")
                plt.show()

                break

    def plot_idx(self, idx):
        count = 0
        for names, param in self.model1.named_parameters():
            for names2, param2 in self.model2.named_parameters():
                if names2 == names:
                    break
            if count == idx:
                weights_list1 = param.data.cpu().numpy().flatten()
                weights_list2 = param2.data.cpu().numpy().flatten()

                plt.figure(figsize=(10, 5))
                plt.subplot(1, 2, 1)
                plt.title(names)
                mini = torch.min(weights_list1)
                maxi = torch.max(weights_list1)
                plt.xlim(mini, maxi)
                plt.hist(weights_list1, bins=50, alpha=0.7)
                plt.subplot(1, 2, 2)
                plt.title(names)
                plt.xlim(mini, maxi)
                plt.hist(weights_list2, bins=50, alpha=0.7)
                plt.show()

                break
            count += 1

    def plot_whole_sep(self):
        for idx in range(self.amount_of_param):
            self.plot_idx(idx)

    def ana_comp(self):
        for names, param in self.model1.named_parameters():
            for names2, param2 in self.model2.named_parameters():
                if names2 == names:
                    break
            max_ratio = torch.max(param) / torch.max(param2)
            min_ratio = torch.min(param) / torch.min(param2)
            mean_ratio = torch.mean(param) / torch.mean(param2)
            std_ratio = torch.std(param) / torch.std(param2)
            print(
                "name = {} | max ratio = {} | min ratio = {} | mean ratio = {} | std ratio = {}".format(
                    names, max_ratio, min_ratio, mean_ratio, std_ratio
                )
            )

    def grad_comp(self):
        for keys in self.grad1:
            max_ratio = torch.max(self.grad1[keys]) / torch.max(self.grad2[keys])
            min_ratio = torch.min(self.grad1[keys]) / torch.min(self.grad2[keys])
            mean_ratio = torch.mean(self.grad1[keys]) / torch.mean(self.grad2[keys])
            std_ratio = torch.std(self.grad1[keys]) / torch.std(self.grad2[keys])
            print(
                "name = {} | max ratio = {} | min ratio = {} | mean ratio = {} | std ratio = {}".format(
                    keys, max_ratio, min_ratio, mean_ratio, std_ratio
                )
            )

    def print_grad(self):
        for keys, values in self.grad2.items():
            print("{} : {}".format(keys, values))

    def show_count(self):
        print(self.amount_of_param)


"""
count = 0
path_list = []
for large_epoch in range(1, 4):

    while True:
        count += 1
        path = '/content/drive/MyDrive/Colab Notebooks/Simple_DE/Checkpoint/drawing_weight/weight_{}_{}.pth'.format(large_epoch, count)
        path_list.append(path)
        if count % 18 == 0:
            break

path_list
"""


class plot:
    def __init__(self, path_list):
        self.path_list = path_list
        # checkpoint = torch.load(path, map_location=torch.device(device))
        # self.grad1 = checkpoint['gradients']
        # model = Model(config)
        # model.load_state_dict(checkpoint['model_state_dict'])
        # self.model1 = model
        # self.path_list = path_list
        # del model
        # model = Model(config)
        # # checkpoint = torch.load(weight_path2, map_location=torch.device(device))
        # self.grad2 = checkpoint['gradients']
        # model.load_state_dict(checkpoint['model_state_dict'])
        # self.model2 = model

        # count = 0
        # for name, param in self.model1.named_parameters():
        #     count += 1
        # self.amount_of_param = count

    def draw_grad(self, epoch_interval, param_interval, legend=True, device="cuda"):
        output_list = []  # row代表不同的epochs column代表不同的params
        keys_list = []
        count = 0
        x_coor = []
        for idx in range(epoch_interval[0], epoch_interval[1]):
            x_coor.append(idx)
            file = self.path_list[idx]  # traverse epoch
            tmp_list = []
            check = torch.load(file, map_location=torch.device(device))
            grad = check["gradients"]
            if count == 0:
                count += 1
                keys_list = list(grad.keys())
                keys_list = keys_list[param_interval[0] : param_interval[1]]
            for key in keys_list:
                summ = torch.mean(torch.abs(grad[key]))
                tmp_list.append(summ)
            output_list.append(tmp_list)
        plt.figure(figsize=(8, 6))  # 设置图形大小
        for col in range(len(output_list[0])):
            column_data = []
            for row in output_list:
                column_data.append(row[col])
            plt.plot(x_coor, column_data, label=keys_list[col])

        plt.xlabel("Epochs")  # 设置 x 轴标签
        plt.ylabel("Values")  # 设置 y 轴标签
        plt.title("Lines for Each Column")  # 设置标题
        if legend:
            plt.legend()  # 添加图例
        plt.grid(True)  # 添加网格线
        plt.show()  # 显示图形

    def count_param(self, device="cuda"):
        file = self.path_list[0]
        check = torch.load(file, map_location=torch.device(device))
        grad = check["gradients"]
        keys_list = list(grad.keys())
        print("there are {} many gradients groups".format(len(keys_list)))


"""
plotting = plot(path_list)
epoch_interval = [1, 20]
for idx in range(50):
    param_interval = [idx * 10, (idx + 1) * 10]
    plotting.draw_grad(epoch_interval, param_interval, legend = False)
"""

"""
plotting = plot(path_list)
epoch_interval = [20, 50]
for idx in range(50):
    param_interval = [idx * 10, (idx + 1) * 10]
    plotting.draw_grad(epoch_interval, param_interval, legend = False)
"""

"""
#reference mode

beta_schedule = config['diffusion']['beta_schedule']
start_schedule = config['diffusion']['beta_start']
end_schedule = config['diffusion']['beta_end']
timesteps = config['diffusion']['num_diffusion_timesteps']
diff = DiffusionModel(beta_schedule, start_schedule, end_schedule, timesteps)
model = Model(config)
model = model.to(device)
ans1, ans2 = diff.backward(model, img, weight_path, 1) # img should have 4 dimension
"""

"""
# convert back into depth map
with torch.inference_mode():
    final_ans = tensor_to_depth(depth2, DEPTH_MEAN, DEPTH_STD)
    final_ans = torch.squeeze(final_ans, dim = 0).to('cpu').numpy()
"""