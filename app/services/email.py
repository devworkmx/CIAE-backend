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

    # URL directa de validación con el token o la página general
    enlace_validacion = f"{settings.FRONTEND_URL.rstrip('/')}/validar/{token_publico}"

    texto_vigencia = (
        f"Vigente hasta el: <strong>{fecha_vigencia}</strong>"
        if tiene_vigencia and fecha_vigencia
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

        <!-- Encabezado Institucional -->
        <tr>
          <td align="center" style="background-color: #1b3a6b; padding: 30px 20px; color: #ffffff;">
            <h1 style="margin: 0; font-size: 22px; font-weight: 700; letter-spacing: 0.5px;">Sistema de Certificación Institucional</h1>
            <p style="margin: 6px 0 0; font-size: 13px; color: #e2e8f0; text-transform: uppercase; letter-spacing: 1px;">Notificación de Emisión Oficial</p>
          </td>
        </tr>

        <!-- Cuerpo del Correo -->
        <tr>
          <td style="padding: 30px;">
            <p style="font-size: 16px; margin: 0 0 16px; color: #0f172a;">
              Estimado(a) <strong>{alumno_nombre}</strong>,
            </p>
            <p style="font-size: 14px; line-height: 1.6; margin: 0 0 24px; color: #475569;">
              Nos complace informarle que se ha emitido formalmente su certificado correspondiente a la acreditación del siguiente programa académico:
            </p>

            <!-- Tarjeta de Detalles -->
            <div style="background-color: #f8fafc; border-left: 4px solid #1b3a6b; padding: 18px; border-radius: 6px; margin-bottom: 24px;">
              <p style="margin: 0 0 8px; font-size: 14px;"><strong>Programa:</strong> {curso_nombre}</p>
              <p style="margin: 0 0 8px; font-size: 14px;"><strong>Folio Oficial:</strong> <span style="font-family: monospace; background-color: #e2e8f0; padding: 2px 6px; border-radius: 4px;">{folio}</span></p>
              <p style="margin: 0 0 8px; font-size: 14px;"><strong>Instructor / Emisor:</strong> {instructor}</p>
              <p style="margin: 0; font-size: 13px; color: #64748b;">{texto_vigencia}</p>
            </div>

            <!-- Botón CTA de Verificación -->
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

        <!-- Pie de página -->
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
