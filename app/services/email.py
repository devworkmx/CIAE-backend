import html
import resend
from app.config import settings

resend.api_key = settings.RESEND_API_KEY


def enviar_correo_certificado(
    destinatario: str,
    alumno_nombre: str,
    curso_nombre: str,
    folio: str,
    token_publico: str,
    instructor: str,
    tiene_vigencia: bool,
    fecha_vigencia: str | None = None,
):
    if not settings.RESEND_API_KEY or not destinatario:
        return

    enlace_validacion = f"{settings.FRONTEND_URL.rstrip('/')}/validar/{token_publico}"

    alumno_nombre = html.escape(alumno_nombre or "")
    curso_nombre = html.escape(curso_nombre or "")
    folio = html.escape(folio or "")
    instructor = html.escape(instructor or "")
    fecha_vigencia_segura = html.escape(fecha_vigencia) if fecha_vigencia else None

    texto_vigencia = (
        f"Vigente hasta el: <strong>{fecha_vigencia_segura}</strong>"
        if tiene_vigencia and fecha_vigencia_segura
        else "Vigencia: <strong>Permanente / Sin caducidad</strong>"
    )

    html_contenido = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Emisión de Certificado</title>
    </head>
    <body style="margin: 0; padding: 0; background-color: #f1f5f9; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #334155;">
      <table align="center" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 600px; margin: 30px auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">

        <tr>
          <td align="center" style="background-color: #1b3a6b; padding: 30px 20px; color: #ffffff;">
            <h1 style="margin: 0; font-size: 22px; font-weight: 700; letter-spacing: 0.5px;">Sistema de Certificación Institucional</h1>
            <p style="margin: 6px 0 0; font-size: 13px; color: #e2e8f0; text-transform: uppercase; letter-spacing: 1px;">Notificación de Emisión Oficial</p>
          </td>
        </tr>

        <tr>
          <td style="padding: 30px;">
            <p style="font-size: 16px; margin: 0 0 16px; color: #0f172a;">
              Estimado(a) <strong>{alumno_nombre}</strong>,
            </p>
            <p style="font-size: 14px; line-height: 1.6; margin: 0 0 24px; color: #475569;">
              Nos complace informarle que se ha emitido formalmente su certificado correspondiente a la acreditación del siguiente programa académico:
            </p>

            <div style="background-color: #f8fafc; border-left: 4px solid #1b3a6b; padding: 18px; border-radius: 6px; margin-bottom: 24px;">
              <p style="margin: 0 0 8px; font-size: 14px;"><strong>Programa:</strong> {curso_nombre}</p>
              <p style="margin: 0 0 8px; font-size: 14px;"><strong>Folio Oficial:</strong> <span style="font-family: monospace; background-color: #e2e8f0; padding: 2px 6px; border-radius: 4px;">{folio}</span></p>
              <p style="margin: 0 0 8px; font-size: 14px;"><strong>Instructor / Emisor:</strong> {instructor}</p>
              <p style="margin: 0; font-size: 13px; color: #64748b;">{texto_vigencia}</p>
            </div>

            <table align="center" border="0" cellpadding="0" cellspacing="0" style="margin: 30px auto 20px;">
              <tr>
                <td align="center" style="border-radius: 8px; background-color: #1b3a6b;">
                  <a href="{enlace_validacion}" target="_blank" style="font-size: 14px; font-weight: 600; color: #ffffff; text-decoration: none; padding: 12px 28px; display: inline-block; border-radius: 8px;">
                    Verificar Autenticidad del Certificado
                  </a>
                </td>
              </tr>
            </table>

            <p style="font-size: 12px; color: #94a3b8; text-align: center; margin: 16px 0 0;">
              O copie y pegue el siguiente enlace en su navegador:<br>
              <a href="{enlace_validacion}" style="color: #2563eb; word-break: break-all;">{enlace_validacion}</a>
            </p>
          </td>
        </tr>

        <tr>
          <td style="background-color: #f8fafc; padding: 20px; text-align: center; border-top: 1px solid #e2e8f0; font-size: 12px; color: #64748b;">
            Este es un correo automatizado generado por el sistema de acreditación académica. Por favor, no responda a este mensaje.
          </td>
        </tr>
      </table>
    </body>
    </html>
    """

    try:
        resend.Emails.send({
            "from": settings.RESEND_FROM_EMAIL,
            "to": destinatario,
            "subject": f"Emisión de Certificado Oficial - {folio}",
            "html": html_contenido,
        })
    except Exception as e:
        print(f"Error al enviar correo por Resend: {e}")


def enviar_correo_renovacion_certificado(
    destinatario: str,
    alumno_nombre: str,
    curso_nombre: str,
    folio: str,
    token_publico: str,
    nueva_fecha_vigencia: str,
    meses_renovados: int,
):
    """
    Notifica al alumno que su certificado ha sido reactivado y extendido
    aclarando que su código QR físico original sigue siendo válido.
    """
    if not settings.RESEND_API_KEY or not destinatario:
        return

    enlace_validacion = f"{settings.FRONTEND_URL.rstrip('/')}/validar/{token_publico}"

    alumno_nombre = html.escape(alumno_nombre or "")
    curso_nombre = html.escape(curso_nombre or "")
    folio = html.escape(folio or "")
    nueva_fecha_vigencia_segura = html.escape(nueva_fecha_vigencia or "")

    html_contenido = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Renovación de Certificado</title>
    </head>
    <body style="margin: 0; padding: 0; background-color: #f1f5f9; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #334155;">
      <table align="center" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 600px; margin: 30px auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">

        <!-- Encabezado de Renovación (Verde Éxito) -->
        <tr>
          <td align="center" style="background-color: #065f46; padding: 30px 20px; color: #ffffff;">
            <h1 style="margin: 0; font-size: 22px; font-weight: 700; letter-spacing: 0.5px;">Sistema de Certificación Institucional</h1>
            <p style="margin: 6px 0 0; font-size: 13px; color: #a7f3d0; text-transform: uppercase; letter-spacing: 1px;">Acreditación Renovada Exitosamente</p>
          </td>
        </tr>

        <!-- Contenido -->
        <tr>
          <td style="padding: 30px;">
            <p style="font-size: 16px; margin: 0 0 16px; color: #0f172a;">
              Estimado(a) <strong>{alumno_nombre}</strong>,
            </p>
            <p style="font-size: 14px; line-height: 1.6; margin: 0 0 20px; color: #475569;">
              Le informamos que la vigencia de su certificado ha sido reactivada y renovada por un periodo de <strong>{meses_renovados} meses</strong> en nuestro padrón oficial.
            </p>

            <!-- Resumen de Renovación -->
            <div style="background-color: #f0fdf4; border-left: 4px solid #059669; padding: 18px; border-radius: 6px; margin-bottom: 24px;">
              <p style="margin: 0 0 8px; font-size: 14px;"><strong>Programa / Curso:</strong> {curso_nombre}</p>
              <p style="margin: 0 0 8px; font-size: 14px;"><strong>Folio Registrado:</strong> <span style="font-family: monospace; background-color: #dcfce7; color: #065f46; padding: 2px 6px; border-radius: 4px; font-weight: bold;">{folio}</span></p>
              <p style="margin: 0; font-size: 14px; color: #065f46;"><strong>Nueva Fecha Límite:</strong> {nueva_fecha_vigencia_segura}</p>
            </div>

            <!-- Aviso sobre el QR físico -->
            <div style="background-color: #eff6ff; border: 1px solid #bfdbfe; padding: 14px; border-radius: 8px; margin-bottom: 24px;">
              <p style="margin: 0; font-size: 12px; line-height: 1.5; color: #1e40af;">
                ℹ️ <strong>Importante sobre su documento físico:</strong> No requiere reimprimir su constancia ni generar un nuevo documento. El código QR original ya refleja automáticamente este estatus renovado en el validador oficial.
              </p>
            </div>

            <!-- Botón CTA -->
            <table align="center" border="0" cellpadding="0" cellspacing="0" style="margin: 25px auto 15px;">
              <tr>
                <td align="center" style="border-radius: 8px; background-color: #065f46;">
                  <a href="{enlace_validacion}" target="_blank" style="font-size: 14px; font-weight: 600; color: #ffffff; text-decoration: none; padding: 12px 28px; display: inline-block; border-radius: 8px;">
                    Consultar Validación en Tiempo Real
                  </a>
                </td>
              </tr>
            </table>

            <p style="font-size: 12px; color: #94a3b8; text-align: center; margin: 16px 0 0;">
              O ingrese directamente mediante la URL:<br>
              <a href="{enlace_validacion}" style="color: #2563eb; word-break: break-all;">{enlace_validacion}</a>
            </p>
          </td>
        </tr>

        <tr>
          <td style="background-color: #f8fafc; padding: 20px; text-align: center; border-top: 1px solid #e2e8f0; font-size: 12px; color: #64748b;">
            Notificación automática de vigencia académica. Por favor, no responda a este mensaje.
          </td>
        </tr>
      </table>
    </body>
    </html>
    """

    try:
        resend.Emails.send({
            "from": settings.RESEND_FROM_EMAIL,
            "to": destinatario,
            "subject": f"Renovación de Certificado Oficial - {folio}",
            "html": html_contenido,
        })
    except Exception as e:
        print(f"Error al enviar correo de renovación por Resend: {e}")
