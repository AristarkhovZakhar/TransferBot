import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim

from PIL import Image

import torchvision.transforms as transforms
import torchvision.models as models

import copy

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
imsize = 512 if torch.cuda.is_available() else 256  # use small size if no gpu

loader = transforms.Compose([
    transforms.Resize(imsize),
    transforms.CenterCrop(imsize),
    transforms.ToTensor()])


def image_loader(image_name):  # Отрисовка изображений из тензора
    image = Image.open(image_name)
    image = loader(image).unsqueeze(0)
    return image.to(device, torch.float)


unloader = transforms.ToPILImage()


class ContentLoss(nn.Module):

    def __init__(self, target, ):
        super(ContentLoss, self).__init__()
        self.target = target.detach()
        self.loss = F.mse_loss(self.target, self.target)  # нужно определить хоть как-то,
        # поскольку вылезет ошибка при обращении до forward к этому полю

    def forward(self, input):
        self.loss = F.mse_loss(input, self.target)
        return input


# Матрица Грама

def Gram_matrix(input):
    batch_size, h, w, feature_map_num = input.size()  # batch_size = 1, (h,w) = dimensions of a feature map
    features = input.view(batch_size * h, w * feature_map_num)  # векторизируем карты сверток
    G = torch.mm(features, features.t())  # mm - matrix mul
    return G.div(batch_size * h * w * feature_map_num)  # 'normalize'


class StyleLoss(nn.Module):
    def __init__(self, target_feature):
        super(StyleLoss, self).__init__()
        self.target = Gram_matrix(target_feature).detach()
        self.loss = F.mse_loss(self.target, self.target)  # нужно определить хоть как-то,
        # поскольку вылезет ошибка при обращении до forward к этому полю

    def forward(self, input):
        G = Gram_matrix(input)
        self.loss = F.mse_loss(G, self.target)
        return input


cnn = models.vgg19(pretrained=True).features.to(device).eval()

# Параметры нормализации при обучении VGG
cnn_norm_mean = torch.tensor([0.485, 0.456, 0.406]).to(device)
cnn_norm_std = torch.tensor([0.229, 0.224, 0.225]).to(device)


# create a module to normalize input image so we can easily put it in a
# nn.Sequential
class Normalization(nn.Module):
    def __init__(self, mean, std):
        super(Normalization, self).__init__()
        self.mean = torch.tensor(mean).view(-1, 1, 1)
        self.std = torch.tensor(std).view(-1, 1, 1)

    def forward(self, img):
        # normalize img
        return (img - self.mean) / self.std


# Конфиг сети VGG-19
content_layers_default = ['conv_4']
style_layers_default = ['conv_1', 'conv_2', 'conv_3', 'conv_4', 'conv_5']


def get_style_model_and_losses(cnn, normalization_mean, normalization_std,
                               style_img, content_img,
                               content_layers=content_layers_default,
                               style_layers=style_layers_default):
    # нормализация
    normalization = Normalization(normalization_mean, normalization_std).to(device)

    # списки для лоссов стиля и контента
    content_losses = []
    style_losses = []

    model = nn.Sequential(normalization)

    i = 0
    for layer in cnn.children():
        if isinstance(layer, nn.Conv2d):
            i += 1
            name = 'conv_{}'.format(i)
        elif isinstance(layer, nn.ReLU):
            name = 'relu_{}'.format(i)
            layer = nn.ReLU(inplace=False)
        elif isinstance(layer, nn.MaxPool2d):
            name = 'pool_{}'.format(i)
        elif isinstance(layer, nn.BatchNorm2d):
            name = 'bn_{}'.format(i)
        else:
            raise RuntimeError('Unrecognized layer: {}'.format(layer.__class__.__name__))

        model.add_module(name, layer)

        if name in content_layers:
            # add content loss:
            target = model(content_img).detach()
            content_loss = ContentLoss(target)
            model.add_module("content_loss_{}".format(i), content_loss)
            content_losses.append(content_loss)

        if name in style_layers:
            # add style loss:
            target_feature = model(style_img).detach()
            style_loss = StyleLoss(target_feature)
            model.add_module("style_loss_{}".format(i), style_loss)
            style_losses.append(style_loss)

    # Обрезаем сеть по последнему слою стиля или контента
    for i in range(len(model) - 1, -1, -1):
        if isinstance(model[i], ContentLoss) or isinstance(model[i], StyleLoss):
            break

    model = model[:(i + 1)]

    return model, style_losses, content_losses


def get_input_optimizer(input_img):
    # Алгоритм Бройдена — Флетчера — Гольдфарба — Шанно
    optimizer = optim.LBFGS([input_img])
    return optimizer


def run_style_transfer(cnn, normalization_mean, normalization_std,
                       content_img, style_img, input_img, num_steps=200,
                       style_weight=1000000, content_weight=1):
    # Фрейм с картинками, полученными по ходу обучения
    Image_frame = []

    print('Building the style transfer model...')
    model, style_losses, content_losses = get_style_model_and_losses(cnn,
                                                                     normalization_mean, normalization_std, style_img,
                                                                     content_img)

    # Не прокидываем градиенты на модель, только на картинку
    input_img.requires_grad_(True)
    model.requires_grad_(False)

    optimizer = get_input_optimizer(input_img)

    print('Optimizing..')

    run = [0]
    while run[0] <= num_steps:

        def closure():
            # correct the values of updated input image
            with torch.no_grad():
                input_img.clamp_(0, 1)

            optimizer.zero_grad()
            model(input_img)
            style_score = 0
            content_score = 0

            for sl in style_losses:
                style_score += sl.loss
            for cl in content_losses:
                content_score += cl.loss

            style_score *= style_weight
            content_score *= content_weight

            loss = style_score + content_score
            print(loss)
            loss.backward()

            run[0] += 1
            if run[0] % 5 == 0:
                Image_frame.append(unloader(input_img.clone().squeeze(0).detach()))
                print('В процессе...')
            return style_score + content_score

        optimizer.step(closure)

    # Обрезаем каналы
    with torch.no_grad():
        input_img.clamp_(0, 1)

    return input_img, Image_frame


def make_gif(images):
    images[0].save(
        '1.gif',
        save_all=True,
        append_images=images[1:],  # Срез который игнорирует первый кадр.
        optimize=True,
        duration=200,
        loop=0
    )
