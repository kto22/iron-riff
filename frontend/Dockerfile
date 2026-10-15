FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html style.css fonts.css app.js /usr/share/nginx/html/
COPY fonts /usr/share/nginx/html/fonts
RUN chmod -R a+rX /usr/share/nginx/html
