from sevici_utiles import *

def test_selecciona_color():
    e1 = EstacionSevici("Est1", "Dir1", 0.0, 0.0, 10, 5, 8)  # 80% bicis
    e2 = EstacionSevici("Est2", "Dir2", 0.0, 0.0, 10, 5, 4)  # 40% bicis
    e3 = EstacionSevici("Est3", "Dir3", 0.0, 0.0, 10, 5, 2)  # 20% bicis
    e4 = EstacionSevici("Est4", "Dir4", 0.0, 0.0, 0, 0, 0)   # capacidad 0

    assert selecciona_color(e1) == "green"
    assert selecciona_color(e2) == "orange"
    assert selecciona_color(e3) == "red"
    assert selecciona_color(e4) == "gray"

def test_estaciones_con_disponibilidad():
    e1 = EstacionSevici("Est1", "Dir1", 0.0, 0.0, 10, 5, 8)  # 80% bicis
    e2 = EstacionSevici("Est2", "Dir2", 0.0, 0.0, 10, 5, 4)  # 40% bicis
    e3 = EstacionSevici("Est3", "Dir3", 0.0, 0.0, 10, 5, 2)  # 20% bicis
    e4 = EstacionSevici("Est4", "Dir4", 0.0, 0.0, 0, 0, 0)   # capacidad 0

    estaciones = [e1, e2, e3, e4]

    res1 = busca_estaciones_con_disponibilidad(estaciones, 0.5)
    assert res1 == [e1]

    res2 = busca_estaciones_con_disponibilidad(estaciones, 0.3)
    assert res2 == [e1, e2]

    res3 = busca_estaciones_con_disponibilidad(estaciones, 0.0)
    assert res3 == [e1, e2, e3]

def test_estacion_mas_cercana():
    e1 = EstacionSevici("Est1", "Dir1", 0.0, 0.0, 10, 5, 3)
    e2 = EstacionSevici("Est2", "Dir2", 1.4, 1.1, 10, 5, 0)
    e3 = EstacionSevici("Est3", "Dir3", 2.0, 2.0, 10, 5, 5)

    estaciones = [e1, e2, e3]

    punto = (1.5, 1.5)
    mas_cercana = busca_estacion_mas_cercana(estaciones, punto)
    assert mas_cercana == e3

def test_calcula_ruta():
    e1 = EstacionSevici("Est1", "Dir1", 0.0, 0.0, 10, 5, 3)  # 3 bicis
    e2 = EstacionSevici("Est2", "Dir2", 5.0, 5.0, 10, 5, 0)  # 0 bicis
    e3 = EstacionSevici("Est3", "Dir3", 10.0, 10.0, 10, 5, 4) # 4 bicis

    estaciones = [e1, e2, e3]

    inicio = (1.0, 1.0)
    fin = (9.0, 9.0)

    estacion_inicio, estacion_fin = calcula_ruta(estaciones, inicio, fin)
    assert estacion_inicio == e1
    assert estacion_fin == e3

def test_busca_estacion_direccion():
    e1 = EstacionSevici("Est1", "Calle A", 0.0, 0.0, 10, 5, 3)
    e2 = EstacionSevici("Est2", "Calle B", 1.0, 1.0, 10, 5, 4)
    estaciones = [e1, e2]

    direccion_buscada = "b"
    estaciones_encontradas = busca_estaciones_direccion(estaciones, direccion_buscada)
    assert estaciones_encontradas == [e2]

def test_calcula_estadisticas():
    e1 = EstacionSevici("Est1", "Dir1", 0.0, 0.0, 10, 5, 3)
    e2 = EstacionSevici("Est2", "Dir2", 1.0, 1.0, 20, 10, 8)
    e3 = EstacionSevici("Est3", "Dir3", 2.0, 2.0, 15, 7, 5)

    estaciones = [e1, e2, e3]

    total_bicis_libres, total_capacidad, porcentaje_ocupacion, total_estaciones = calcula_estadisticas(estaciones)
    assert total_bicis_libres == 16  # 3 + 8 + 5
    assert total_capacidad == 45      # 10 + 20 + 15
    assert abs(porcentaje_ocupacion - 64.44) < 0.1  # Aproximadamente 64.44%
    assert total_estaciones == 3
       

# Descomenta las llamadas a las funciones de prueba a medida que vayas 
# resolviendo los ejercicios
test_selecciona_color()
#test_calcula_estadisticas()
#test_busca_estacion_direccion()
#test_estaciones_con_disponibilidad()
#test_estacion_mas_cercana()
#test_calcula_ruta()
print("Todas las pruebas pasaron correctamente.")
