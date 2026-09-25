# Modelo predictivo

`RandomForestClassifier`: 200 árboles, profundidad máxima 6, mínimo 10 muestras por hoja, clases balanceadas, semilla 42. Combina árboles entrenados con variación aleatoria y promedia estimaciones de clase.

Features, en el orden compartido por entrenamiento e inferencia:

1. `pct_pagos_tarde`: proporción de pagos con días de atraso positivos.
2. `promedio_dias_atraso`: promedio de días solo entre pagos tardíos.
3. `num_pagos_historicos`: registros con días de atraso conocidos.
4. `monto_promedio_pago`: monto promedio de esos registros.
5. `monto_pendiente_actual`: saldo de deudas Pendiente/En Mora.
6. `num_deudas_activas`: cantidad de deudas con esos estatus.

Sin historial se usan supuestos de 0.3 de pagos tardíos, 5 días de atraso y monto promedio 0. No son valores neutrales demostrados empíricamente.

La etiqueta 1 representa pago a tiempo. `score_riesgo = round(1 - probabilidad_pago_a_tiempo, 3)`. Alto >=0.66, medio >=0.33 y bajo <0.33. Prioridad = score × saldo pendiente. Sin cálculo, el score inicial 0 no equivale a evidencia de buen pagador; el segmento se muestra sin calcular.

El script genera 2,000 registros mediante distribuciones y una regla probabilística con ruido; divide 80% entrenamiento / 20% evaluación estratificada. Imprime precision, recall, F1 y AUC-ROC. **Toda precisión actual corresponde a datos sintéticos**, no a una cartera real ni a probabilidad calibrada. Las reglas de generación son supuestos de demostración.

`python -m app.ml.train_model` reemplaza el bundle joblib y requiere reiniciar backend. Respaldar el artefacto antes. Solo cargar archivos propios: joblib puede ejecutar código al deserializar. Para producción se requiere historial real anonimizado, evaluación temporal, calibración, revisión de equidad y supervisión humana. La IA generativa redacta y no modifica el score.
