idf_component_register(SRCS "main.c" "quota.c" "screen_ui.c" INCLUDE_DIRS "." REQUIRES esp_wifi esp_event esp_netif esp_http_client esp_http_server mbedtls nvs_flash json lwip)
