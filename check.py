import torch
print("number of gpus devices:", torch.cuda.device_count())
print("gpu name:", torch.cuda.get_device_name(0))