# TransferBot
Телеграм-бот, с помощью которого можно переносить стиль фотографий.

# О модели 
В данном проекте использовался алгоритм переноса стиля с одного изображения на другое(Leon A. Gatys, Alexander S). Обработка изображений проводится при помощи сети VGG-19, алгоритм оптимизации - квазиньютоновский метод *L-BFGS*  (Broyden, Fletcher, Goldfarb, Shanno). Функция потерь состоин из двух различных функций. Первая - *content loss* - вычисляет MSE между картинкой контента и картинкой стиля, вторая - *style loss* вычисляет MSE для матриц Грама изображений(для этого перед подсчетом вытягиваем их в вектор). Соответствующие слои лосса добавлены после слоев свертки, а сама сеть VGG-19 урезана по последнему слою лосса.
 # Пример использования
-  Исходное изображение
 
![](https://sun9-39.userapi.com/impg/0vwz3dB25dP4i8eEATo5YZlNLi8NUDUdzHsAkA/nVBInkxmGt4.jpg?size=768x1024&quality=95&sign=067448c986ee732353d896b51b06263f&type=album)

- Изображение стиля

![](https://i2.wp.com/arts-dnevnik.ru/wp-content/uploads/2017/02/IMG_2723.jpg)

- Получившееся изображение

![](https://sun9-28.userapi.com/impg/niJoLNPQ0pnd6TxftEz-ocZ9ZuBwyL8XrOWmkA/AI_M9ZxX3yE.jpg?size=512x512&quality=96&sign=d1f4bffc0ebfa48ae38eb0903f41559a&type=album)

