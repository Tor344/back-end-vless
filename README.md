# **back-end-vless**
![](https://user-gen-media-assets.s3.amazonaws.com/seedream_images/85cf06df-9803-4da1-bc8c-ba51f8f590df.png)

## **back-end-vless**
Это сервис для создание/удаления пользователей в рамках vpn/vless 

## Техногогии 
1. python
2. fast-api
3. [vless_manager](https://github.com/Tor344/vless_manager)
   
## Запросы 
### ```new_user/{имя пользователя}```
Создает пользователя с именем, которое было передано в ссылке
Возвращает "link": "ссылка для подключения"
### ```delete_user/{имя пользователя}```
Удоляет пользователя по имени, которорое было передано в ссылке

### ```show_user/```
Возвращает "count_user": "количество пользователей"


## Запуск сервиса

1. ```git clone https://github.com/Tor344/back-end-vless```
2. ```cd back-end-vless```
3. Создайте файл ```.env``` и внесите API токен ```API_TOKEN="ваш токен"``` 
4. ```python -m venv venv```
5. ```source venv/bin/activate```
6. ```pip install -r requirements.txt```
7. ```python installer.py```
8. ```uvicorn main:app --host 0.0.0.0 --port 8000```


