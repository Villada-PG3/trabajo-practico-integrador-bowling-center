from datetime import datetime, time
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    Cliente,
    DetallePedido,
    EstadoPartida,
    EstadoPedido,
    EstadoReserva,
    HorarioAtencion,
    Jugador,
    Lanzamiento,
    Participacion,
    Partida,
    Pedido,
    Pista,
    Producto,
    Reserva,
    TipoPista,
)
from .views import obtener_estado_pistas


class OperacionTests(TestCase):
    def setUp(self):
        self.hoy = timezone.localdate()
        self.ahora = timezone.make_aware(
            datetime.combine(self.hoy, time(18)),
            timezone.get_current_timezone(),
        )
        self.tipo = TipoPista.objects.create(
            nombre="Test",
            descripcion="Pista de prueba",
            precio_hora=Decimal("1000.00"),
            capacidad_maxima=6,
            duracion_minima=1,
        )
        self.pista = self.crear_pista()
        HorarioAtencion.objects.create(
            dia_semana=self.hoy.weekday(),
            hora_apertura=time(8),
            hora_cierre=time(23),
        )
        self.staff = get_user_model().objects.create_user(
            username="trabajador",
            password="clave-segura",
            is_staff=True,
        )

    def crear_pista(self, disponible=True):
        return Pista.objects.create(
            tipo_pista=self.tipo,
            precio_hora=Decimal("1200.00"),
            disponible=disponible,
        )

    def crear_reserva(
        self,
        pista=None,
        inicio=time(17),
        fin=time(19),
        estado="pendiente_a_pago",
    ):
        cliente = Cliente.objects.create(
            nombre="Cliente de prueba",
            direccion="Calle 123",
            telefono="1122334455",
            email=f"cliente{Cliente.objects.count()}@example.com",
        )
        return Reserva.objects.create(
            cliente=cliente,
            pista=pista or self.pista,
            fecha=self.hoy,
            hora_inicio=inicio,
            hora_fin=fin,
            estado=EstadoReserva.objects.get(nombre=estado),
            cantidad_jugadores=4,
        )

    def ingresar_como_staff(self):
        self.client.force_login(self.staff)

    def test_inicio_muestra_logo_local_sin_wordmark_de_texto(self):
        respuesta = self.client.get(reverse("bowling_center:home"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(
            respuesta,
            "/static/bowling_center/images/pins-logo.jpg",
        )

    def test_operacion_requiere_autenticacion_y_restringe_a_staff(self):
        respuesta = self.client.get(reverse("bowling_center:operacion"))
        self.assertRedirects(
            respuesta,
            f"{reverse('bowling_center:operacion_login')}?next={reverse('bowling_center:operacion')}",
        )

        usuario = get_user_model().objects.create_user(
            username="cliente",
            password="clave-segura",
        )
        self.client.force_login(usuario)
        self.assertEqual(self.client.get(reverse("bowling_center:operacion")).status_code, 403)

    def test_login_solo_acepta_usuarios_staff(self):
        get_user_model().objects.create_user(
            username="cliente",
            password="clave-segura",
        )
        respuesta = self.client.post(
            reverse("bowling_center:operacion_login"),
            {"username": "cliente", "password": "clave-segura"},
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "exclusiva para el personal")

    def test_staff_login_y_logout(self):
        respuesta = self.client.post(
            reverse("bowling_center:operacion_login"),
            {"username": "trabajador", "password": "clave-segura"},
        )
        self.assertRedirects(respuesta, reverse("bowling_center:gestion"))
        self.assertEqual(self.client.get(reverse("bowling_center:gestion")).status_code, 200)
        self.assertEqual(
            self.client.get(reverse("bowling_center:operacion")).status_code,
            200,
        )

        respuesta = self.client.post(reverse("bowling_center:operacion_logout"))
        self.assertRedirects(respuesta, reverse("bowling_center:home"))
        self.assertRedirects(
            self.client.get(reverse("bowling_center:operacion")),
            f"{reverse('bowling_center:operacion_login')}?next={reverse('bowling_center:operacion')}",
        )

    def test_staff_crea_tipo_pista_y_luego_pista_desde_el_panel(self):
        self.ingresar_como_staff()
        respuesta = self.client.post(
            reverse("bowling_center:crear_tipo_pista"),
            {
                "nombre": "VIP",
                "descripcion": "Pista premium",
                "precio_hora": "2500.00",
                "capacidad_maxima": "8",
                "duracion_minima": "2",
            },
        )
        self.assertRedirects(respuesta, reverse("bowling_center:gestion_tipos"))
        tipo = TipoPista.objects.get(nombre="VIP")

        respuesta = self.client.post(
            reverse("bowling_center:crear_pista"),
            {
                "tipo_pista": tipo.pk,
                "precio_hora": "",
                "disponible": "on",
            },
        )
        self.assertRedirects(respuesta, reverse("bowling_center:gestion_pistas"))
        pista = Pista.objects.get(tipo_pista=tipo)
        self.assertTrue(pista.disponible)
        self.assertIsNone(pista.precio_hora)
        self.assertContains(
            self.client.get(reverse("bowling_center:gestion_pistas")),
            f"Pista {pista.numero_pista}",
        )

        respuesta = self.client.post(
            reverse("bowling_center:editar_pista", args=[pista.pk]),
            {"tipo_pista": tipo.pk, "precio_hora": "", "disponible": ""},
        )
        self.assertRedirects(respuesta, reverse("bowling_center:gestion_pistas"))
        pista.refresh_from_db()
        self.assertFalse(pista.disponible)

    def test_staff_administra_horarios_y_no_puede_borrar_pista_reservada(self):
        self.ingresar_como_staff()
        respuesta = self.client.post(
            reverse("bowling_center:crear_horario"),
            {
                "dia_semana": self.hoy.weekday(),
                "hora_apertura": "09:00",
                "hora_cierre": "22:00",
            },
        )
        self.assertRedirects(respuesta, reverse("bowling_center:gestion_horarios"))
        horario = HorarioAtencion.objects.get(hora_apertura=time(9))

        respuesta = self.client.post(
            reverse("bowling_center:editar_horario", args=[horario.pk]),
            {
                "dia_semana": self.hoy.weekday(),
                "hora_apertura": "10:00",
                "hora_cierre": "21:00",
            },
        )
        self.assertRedirects(respuesta, reverse("bowling_center:gestion_horarios"))
        horario.refresh_from_db()
        self.assertEqual(horario.hora_apertura, time(10))

        reserva = self.crear_reserva()
        respuesta = self.client.post(
            reverse("bowling_center:eliminar_pista", args=[self.pista.pk]),
            follow=True,
        )
        self.assertContains(respuesta, "todavía está en uso")
        self.assertTrue(Pista.objects.filter(pk=self.pista.pk).exists())
        self.assertTrue(Reserva.objects.filter(pk=reserva.pk).exists())

    def test_panel_de_gestion_y_catalogos_solo_permiten_staff(self):
        respuesta = self.client.get(reverse("bowling_center:gestion"))
        self.assertRedirects(
            respuesta,
            f"{reverse('bowling_center:operacion_login')}?next={reverse('bowling_center:gestion')}",
        )

        usuario = get_user_model().objects.create_user(
            username="visitante",
            password="clave-segura",
        )
        self.client.force_login(usuario)
        self.assertEqual(self.client.get(reverse("bowling_center:gestion_pistas")).status_code, 403)

    def test_staff_crea_edita_y_administra_productos_de_cafeteria(self):
        self.ingresar_como_staff()
        respuesta = self.client.post(
            reverse("bowling_center:crear_producto"),
            {
                "nombre": "Limonada",
                "descripcion": "Jugo natural",
                "tipo": Producto.BEBIDA,
                "precio": "1200.00",
            },
        )
        self.assertRedirects(respuesta, reverse("bowling_center:gestion_productos"))
        producto = Producto.objects.get(nombre="Limonada")
        self.assertContains(
            self.client.get(reverse("bowling_center:gestion_productos")),
            "Limonada",
        )

        respuesta = self.client.post(
            reverse("bowling_center:editar_producto", args=[producto.pk]),
            {
                "nombre": "Limonada fresca",
                "descripcion": "Jugo natural",
                "tipo": Producto.BEBIDA,
                "precio": "1300.00",
            },
        )
        self.assertRedirects(respuesta, reverse("bowling_center:gestion_productos"))
        producto.refresh_from_db()
        self.assertEqual(producto.nombre, "Limonada fresca")
        self.assertEqual(producto.precio, Decimal("1300.00"))

    def test_agenda_filtra_por_fecha_y_cliente_y_permite_cargar_consumos(self):
        reserva = self.crear_reserva(estado="en_curso")
        producto = Producto.objects.create(
            nombre="Limonada",
            descripcion="",
            precio=Decimal("1200.00"),
            tipo=Producto.BEBIDA,
        )
        comida = Producto.objects.create(
            nombre="Papas",
            descripcion="",
            precio=Decimal("1800.00"),
            tipo=Producto.COMIDA,
        )
        self.ingresar_como_staff()
        query = {"fecha": self.hoy.isoformat(), "cliente": "Cliente de prueba"}

        with patch("bowling_center.views.timezone.localtime", return_value=self.ahora):
            respuesta = self.client.get(
                reverse("bowling_center:operacion_reservas"),
                query,
            )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Cliente de prueba")
        self.assertContains(respuesta, "Limonada")
        self.assertContains(respuesta, "Papas")

        respuesta = self.client.get(
            reverse("bowling_center:operacion_reservas"),
            {"fecha": self.hoy.isoformat(), "cliente": "No existe"},
        )
        self.assertContains(respuesta, "No hay reservas para esta búsqueda")

        respuesta = self.client.post(
            reverse(
                "bowling_center:agregar_pedido_operacion",
                args=[reserva.codigo],
            ),
            {
                "producto": producto.pk,
                "cantidad": "2",
                "fecha": self.hoy.isoformat(),
                "cliente": "Cliente de prueba",
            },
            follow=True,
        )
        self.assertRedirects(
            respuesta,
            f"{reverse('bowling_center:operacion_reservas')}?fecha={self.hoy.isoformat()}&cliente=Cliente+de+prueba",
        )
        pedido = Pedido.objects.get(reserva=reserva)
        detalle = DetallePedido.objects.get(pedido=pedido)
        self.assertEqual(detalle.producto, producto)
        self.assertEqual(detalle.cantidad, 2)
        self.assertEqual(detalle.precio_unitario, Decimal("1200.00"))
        self.assertContains(respuesta, "Se agregó 2 × Limonada")

        producto.precio = Decimal("1500.00")
        producto.save()
        detalle.refresh_from_db()
        self.assertEqual(detalle.precio_unitario, Decimal("1200.00"))

    def test_estado_de_pista_se_cambia_desde_operacion_con_reservas_protegidas(self):
        self.ingresar_como_staff()
        url = reverse(
            "bowling_center:cambiar_disponibilidad_pista",
            args=[self.pista.pk],
        )
        respuesta = self.client.post(
            url,
            {"disponible": "0"},
            follow=True,
        )
        self.assertContains(respuesta, "quedó en mantenimiento")
        self.pista.refresh_from_db()
        self.assertFalse(self.pista.disponible)

        self.client.post(url, {"disponible": "1"})
        self.pista.refresh_from_db()
        self.assertTrue(self.pista.disponible)

        self.crear_reserva()
        respuesta = self.client.post(
            url,
            {"disponible": "0"},
            follow=True,
        )
        self.assertContains(respuesta, "tiene reservas vigentes o futuras")
        self.pista.refresh_from_db()
        self.assertTrue(self.pista.disponible)

    def test_mapa_muestra_estados_de_pistas_y_reservas(self):
        ocupada = self.crear_pista()
        reservada = self.crear_pista()
        mantenimiento = self.crear_pista(disponible=False)
        self.crear_reserva(ocupada, estado="pagada")
        self.crear_reserva(
            reservada,
            inicio=time(18, 30),
            fin=time(20, 30),
        )

        estados = obtener_estado_pistas(self.ahora)
        por_numero = {item["pista"].pk: item for item in estados}

        self.assertEqual(por_numero[self.pista.pk]["estado"], "libre")
        self.assertEqual(por_numero[ocupada.pk]["estado"], "ocupada")
        self.assertEqual(por_numero[reservada.pk]["estado"], "reservada")
        self.assertEqual(por_numero[mantenimiento.pk]["estado"], "mantenimiento")

        self.ingresar_como_staff()
        with patch("bowling_center.views.timezone.localtime", return_value=self.ahora):
            respuesta = self.client.get(reverse("bowling_center:operacion"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Mantenimiento")
        self.assertContains(respuesta, "Cliente de prueba")

    def test_checkin_cambia_reserva_a_en_curso_y_avisa(self):
        reserva = self.crear_reserva()
        self.ingresar_como_staff()

        with patch("bowling_center.views.timezone.localtime", return_value=self.ahora):
            respuesta = self.client.post(
                reverse("bowling_center:operacion_llegada", args=[reserva.codigo]),
                follow=True,
            )

        reserva.refresh_from_db()
        self.assertEqual(reserva.estado.nombre, "en_curso")
        self.assertContains(respuesta, "Se registró la llegada")

    def test_no_show_cancela_reserva_solo_luego_de_quince_minutos(self):
        reserva = self.crear_reserva(inicio=time(18), fin=time(20))
        ahora = self.ahora.replace(minute=20)
        self.ingresar_como_staff()

        with patch("bowling_center.views.timezone.localtime", return_value=ahora):
            respuesta = self.client.post(
                reverse("bowling_center:operacion_ausencia", args=[reserva.codigo]),
                follow=True,
            )

        reserva.refresh_from_db()
        self.assertEqual(reserva.estado.nombre, "cancelada")
        self.assertContains(respuesta, "la pista está libre")
        self.assertEqual(
            obtener_estado_pistas(ahora)[0]["estado"],
            "libre",
        )

    def test_no_show_antes_de_quince_minutos_no_cambia_reserva(self):
        reserva = self.crear_reserva(inicio=time(18), fin=time(20))
        ahora = self.ahora.replace(minute=14)
        self.ingresar_como_staff()

        with patch("bowling_center.views.timezone.localtime", return_value=ahora):
            respuesta = self.client.post(
                reverse("bowling_center:operacion_ausencia", args=[reserva.codigo]),
                follow=True,
            )

        reserva.refresh_from_db()
        self.assertEqual(reserva.estado.nombre, "pendiente_a_pago")
        self.assertContains(respuesta, "15 minutos después")

    def test_caja_cierra_pedidos_cobra_precios_congelados_y_finaliza(self):
        reserva = self.crear_reserva(estado="en_curso")
        producto = Producto.objects.create(
            nombre="Bebida de prueba",
            descripcion="",
            precio=Decimal("200.00"),
            tipo=Producto.BEBIDA,
        )
        pedido = Pedido.objects.create(
            reserva=reserva,
            estado=EstadoPedido.objects.get(nombre="abierto"),
        )
        detalle = DetallePedido.objects.create(
            pedido=pedido,
            producto=producto,
            cantidad=2,
            precio_unitario=Decimal("180.00"),
        )
        self.ingresar_como_staff()

        respuesta = self.client.get(
            reverse("bowling_center:caja", args=[reserva.codigo])
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            respuesta.context["reserva"].calcularCostoTotal(),
            Decimal("2760.00"),
        )
        self.assertContains(respuesta, "$ 180,00 c/u")

        self.client.post(
            reverse(
                "bowling_center:cerrar_pedido",
                args=[reserva.codigo, pedido.pk],
            )
        )
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado.nombre, "cerrado")

        producto.precio = Decimal("999.00")
        producto.save()
        detalle.refresh_from_db()
        self.assertEqual(detalle.precio_unitario, Decimal("180.00"))

        self.client.post(
            reverse("bowling_center:marcar_pagada", args=[reserva.codigo])
        )
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado.nombre, "pagada")

        respuesta = self.client.get(
            reverse("bowling_center:detalle_reserva", args=[reserva.codigo])
        )
        self.assertContains(respuesta, "Pagada")
        self.assertContains(respuesta, "$ 2760,00")

        self.client.post(
            reverse("bowling_center:finalizar_reserva", args=[reserva.codigo])
        )
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado.nombre, "finalizada")
        respuesta = self.client.get(
            reverse("bowling_center:detalle_reserva", args=[reserva.codigo])
        )
        self.assertContains(respuesta, "Finalizada")
        self.assertContains(respuesta, "$ 2760,00")
        self.assertContains(respuesta, "Descargar datos de la reserva (PDF)")

        respuesta = self.client.get(
            reverse("bowling_center:comprobante_reserva", args=[reserva.codigo])
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta["Content-Type"], "application/pdf")
        self.assertIn("attachment;", respuesta["Content-Disposition"])
        self.assertIn(
            f"comprobante-reserva-{reserva.codigo}.pdf",
            respuesta["Content-Disposition"],
        )
        self.assertTrue(respuesta.content.startswith(b"%PDF-"))
        self.assertGreater(len(respuesta.content), 1000)

    def test_comprobante_pdf_se_descarga_tras_crear_reserva_pendiente(self):
        reserva = self.crear_reserva(estado="pendiente_a_pago")
        detalle = self.client.get(
            reverse("bowling_center:detalle_reserva", args=[reserva.codigo])
        )
        self.assertContains(detalle, "Descargar datos de la reserva (PDF)")

        respuesta = self.client.get(
            reverse("bowling_center:comprobante_reserva", args=[reserva.codigo])
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta["Content-Type"], "application/pdf")
        self.assertIn("attachment;", respuesta["Content-Disposition"])
        self.assertIn(
            f"comprobante-reserva-{reserva.codigo}.pdf",
            respuesta["Content-Disposition"],
        )
        self.assertTrue(respuesta.content.startswith(b"%PDF-"))
        self.assertGreater(len(respuesta.content), 1000)

    def test_partida_explicada_calcula_frames_y_bonificacion_del_decimo(self):
        reserva = self.crear_reserva()
        partida = Partida.objects.create(
            reserva=reserva,
            numero=1,
            fecha_hora_inicio=self.ahora,
            estado=EstadoPartida.objects.get(nombre="pendiente"),
        )
        jugador = Jugador.objects.create(nombre="Ana")
        participacion = Participacion.objects.create(
            partida=partida,
            jugador=jugador,
        )
        tiros_por_frame = {
            1: [10],
            2: [7, 3],
            3: [9, 0],
            4: [0, 0],
            5: [0, 0],
            6: [0, 0],
            7: [0, 0],
            8: [0, 0],
            9: [0, 0],
            10: [10, 7, 3],
        }
        for frame, tiros in tiros_por_frame.items():
            for numero, pinos in enumerate(tiros, start=1):
                Lanzamiento.objects.create(
                    participacion=participacion,
                    numero_frame=frame,
                    numero_lanzamiento=numero,
                    pinos_derribados=pinos,
                )

        self.assertIsNone(participacion.siguienteTiro())
        self.assertEqual(participacion.marcasPorFrame()[0], "X")
        self.assertEqual(participacion.marcasPorFrame()[1], "7 /")
        self.assertEqual(participacion.marcasPorFrame()[9], "X · 7 · 3")
        self.assertEqual(participacion.calcularPuntajeTotal(), 68)

        respuesta = self.client.get(
            reverse("bowling_center:partida", args=[reserva.codigo])
        )
        self.assertContains(respuesta, "Cómo jugar y cargar el puntaje")
        self.assertContains(respuesta, "10 frames por persona")
        self.assertContains(respuesta, "Ana")
        self.assertContains(respuesta, "68")

    def test_no_se_agregan_jugadores_despues_del_primer_tiro(self):
        reserva = self.crear_reserva()
        partida = Partida.objects.create(
            reserva=reserva,
            numero=1,
            fecha_hora_inicio=self.ahora,
            estado=EstadoPartida.objects.get(nombre="pendiente"),
        )
        participacion = Participacion.objects.create(
            partida=partida,
            jugador=Jugador.objects.create(nombre="Ana"),
        )
        Lanzamiento.objects.create(
            participacion=participacion,
            numero_frame=1,
            numero_lanzamiento=1,
            pinos_derribados=4,
        )
        self.client.post(
            reverse("bowling_center:agregar_jugador_partida", args=[reserva.codigo]),
            {"nombre": "Bruno"},
            follow=True,
        )
        self.assertFalse(Jugador.objects.filter(nombre="Bruno").exists())
