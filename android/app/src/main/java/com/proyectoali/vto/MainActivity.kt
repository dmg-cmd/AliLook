package com.proyectoali.vto

import android.Manifest
import android.annotation.SuppressLint
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.MediaStore
import android.util.Base64
import android.view.Gravity
import android.webkit.JavascriptInterface
import android.webkit.PermissionRequest
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.Toast
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricPrompt
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.fragment.app.FragmentActivity
import org.json.JSONObject
import java.io.File
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.HttpURLConnection
import java.net.InetAddress
import java.net.URL
import kotlin.concurrent.thread

class MainActivity : FragmentActivity() {

    private lateinit var webView: WebView
    private lateinit var urlInput: EditText
    private lateinit var btnBuscar: Button
    private var filePathCallback: ValueCallback<Array<Uri>>? = null
    private var camaraUri: Uri? = null
    @Volatile private var pendingSharedImageBase64: String? = null
    @Volatile private var pendingSharedMime: String = "image/jpeg"
    @Volatile private var paginaCargada: Boolean = false
    private var pendingExportBytes: ByteArray? = null
    private var pendingImportPassword: String? = null

    companion object {
        private const val REQ_ARCHIVO = 1001
        private const val REQ_PERMISO_CAMARA = 1002
        private const val REQ_EXPORTAR_PERFIL = 1003
        private const val REQ_IMPORTAR_PERFIL = 1004
        private const val PREFS_NAME = "proyecto_ali_prefs"
        private const val KEY_URL = "servidor_url"
        private const val URL_DEFECTO = "http://127.0.0.1:8000"
        private const val PUERTO_UDP = 8001
        private val sesionTemporal = java.util.concurrent.ConcurrentHashMap<String, String>()
    }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val prefs = getSharedPreferences(PREFS_NAME, MODE_PRIVATE)
        val urlInicial = prefs.getString(KEY_URL, URL_DEFECTO) ?: URL_DEFECTO

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.parseColor("#0F172A"))
        }

        val barra = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            setPadding(16, 16, 16, 16)
            gravity = Gravity.CENTER_VERTICAL
            setBackgroundColor(Color.parseColor("#1E293B"))
        }

        urlInput = EditText(this).apply {
            setText(urlInicial)
            setTextColor(Color.WHITE)
            setHintTextColor(Color.parseColor("#94A3B8"))
            hint = "http://127.0.0.1:8000"
            setSingleLine(true)
            textSize = 13f
            layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
        }

        btnBuscar = Button(this).apply {
            text = "Buscar PC"
            textSize = 12f
            setOnClickListener { buscarServidorAutomaticamente() }
        }

        val btnConectar = Button(this).apply {
            text = "Ir"
            textSize = 12f
            setOnClickListener {
                val url = urlInput.text.toString().trim().trimEnd('/')
                if (url.startsWith("http://") || url.startsWith("https://")) {
                    prefs.edit().putString(KEY_URL, url).apply()
                    webView.loadUrl(url)
                } else {
                    Toast.makeText(this@MainActivity, "Ingresa una URL válida (http://...)", Toast.LENGTH_SHORT).show()
                }
            }
        }

        barra.addView(urlInput)
        barra.addView(btnBuscar)
        barra.addView(btnConectar)

        webView = WebView(this).apply {
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                0,
                1f
            )
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.allowFileAccess = true
            addJavascriptInterface(PuenteBoveda(), "AndroidVault")
            webViewClient = object : WebViewClient() {
                override fun onPageFinished(view: WebView?, url: String?) {
                    super.onPageFinished(view, url)
                    paginaCargada = true
                    enviarPrendaCompartidaAWeb()
                }

                override fun onReceivedError(
                    view: WebView?,
                    request: WebResourceRequest?,
                    error: WebResourceError?
                ) {
                    if (request?.isForMainFrame == true) {
                        val htmlError = """
                            <html><body style="background:#0f172a;color:#f8fafc;font-family:sans-serif;padding:24px;">
                            <h2>No se pudo conectar al servidor</h2>
                            <p>Asegúrate de tener abierto <b>iniciar_servidor.bat</b> en tu PC.</p>
                            <p>Toca <b>Buscar PC</b> arriba para detectar automáticamente tu notebook por USB o Wi-Fi.</p>
                            </body></html>
                        """.trimIndent()
                        view?.loadDataWithBaseURL(null, htmlError, "text/html", "UTF-8", null)
                    }
                }
            }
            webChromeClient = object : WebChromeClient() {
                override fun onPermissionRequest(request: PermissionRequest?) {
                    runOnUiThread {
                        request?.grant(request.resources)
                    }
                }

                override fun onShowFileChooser(
                    webView: WebView?,
                    callback: ValueCallback<Array<Uri>>?,
                    fileChooserParams: FileChooserParams?
                ): Boolean {
                    filePathCallback?.onReceiveValue(null)
                    filePathCallback = callback
                    solicitarFotoOArchivo()
                    return true
                }
            }
        }

        root.addView(barra)
        root.addView(webView)
        setContentView(root)

        ViewCompat.setOnApplyWindowInsetsListener(root) { view, insets ->
            val barrasSistema = insets.getInsets(
                WindowInsetsCompat.Type.systemBars() or WindowInsetsCompat.Type.displayCutout()
            )
            view.setPadding(barrasSistema.left, barrasSistema.top, barrasSistema.right, barrasSistema.bottom)
            insets
        }

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.CAMERA), REQ_PERMISO_CAMARA)
        }

        procesarIntentCompartido(intent)
        webView.loadUrl(urlInicial)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        procesarIntentCompartido(intent)
    }

    private fun procesarIntentCompartido(intent: Intent?) {
        if (intent?.action != Intent.ACTION_SEND) return
        val mime = intent.type ?: "image/jpeg"
        if (!mime.startsWith("image/")) return

        val uri: Uri? = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            intent.getParcelableExtra(Intent.EXTRA_STREAM, Uri::class.java)
        } else {
            @Suppress("DEPRECATION")
            intent.getParcelableExtra(Intent.EXTRA_STREAM)
        }
        if (uri == null) return

        thread {
            try {
                val bytes = contentResolver.openInputStream(uri)?.use { it.readBytes() } ?: return@thread
                val b64 = Base64.encodeToString(bytes, Base64.NO_WRAP)
                pendingSharedImageBase64 = b64
                pendingSharedMime = mime
                sesionTemporal["prendaB64"] = b64
                sesionTemporal["prendaMime"] = mime
                runOnUiThread {
                    if (paginaCargada) {
                        enviarPrendaCompartidaAWeb()
                    }
                }
            } catch (ex: Exception) {
                runOnUiThread {
                    Toast.makeText(this, "No se pudo leer la imagen compartida: ${ex.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun enviarPrendaCompartidaAWeb() {
        val b64 = pendingSharedImageBase64 ?: return
        val mime = pendingSharedMime
        pendingSharedImageBase64 = null
        val b64Esc = JSONObject.quote(b64)
        val mimeEsc = JSONObject.quote(mime)
        webView.evaluateJavascript(
            "window.onPrendaCompartida && window.onPrendaCompartida($b64Esc, $mimeEsc);",
            null
        )
    }

    private fun autenticarYEjecutar(titulo: String, subtitulo: String, alAutenticar: () -> Unit) {
        val bm = BiometricManager.from(this)
        val autenticadores = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            BiometricManager.Authenticators.BIOMETRIC_STRONG or BiometricManager.Authenticators.DEVICE_CREDENTIAL
        } else {
            BiometricManager.Authenticators.BIOMETRIC_WEAK or BiometricManager.Authenticators.DEVICE_CREDENTIAL
        }

        val estado = bm.canAuthenticate(autenticadores)
        if (estado != BiometricManager.BIOMETRIC_SUCCESS) {
            Toast.makeText(
                this,
                "Configura un PIN, patrón o huella en tu celular para proteger tu foto.",
                Toast.LENGTH_LONG
            ).show()
            return
        }

        val executor = ContextCompat.getMainExecutor(this)
        val prompt = BiometricPrompt(
            this,
            executor,
            object : BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                    super.onAuthenticationSucceeded(result)
                    alAutenticar()
                }

                override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                    super.onAuthenticationError(errorCode, errString)
                    Toast.makeText(this@MainActivity, errString, Toast.LENGTH_SHORT).show()
                }
            }
        )

        val builder = BiometricPrompt.PromptInfo.Builder()
            .setTitle(titulo)
            .setSubtitle(subtitulo)

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            builder.setAllowedAuthenticators(autenticadores)
        } else {
            @Suppress("DEPRECATION")
            builder.setDeviceCredentialAllowed(true)
        }

        prompt.authenticate(builder.build())
    }

    inner class PuenteBoveda {
        @JavascriptInterface
        fun listarPerfiles(): String = BovedaPerfil.listarPerfiles(this@MainActivity)

        @JavascriptInterface
        fun obtenerUltimoPerfil(): String = BovedaPerfil.obtenerUltimoPerfil(this@MainActivity)

        @JavascriptInterface
        fun guardarEstadoSesion(clave: String, valor: String) {
            if (valor.isEmpty()) sesionTemporal.remove(clave) else sesionTemporal[clave] = valor
        }

        @JavascriptInterface
        fun obtenerEstadoSesion(clave: String): String = sesionTemporal[clave] ?: ""

        @JavascriptInterface
        fun guardarPerfil(nombre: String, jsonDatos: String, fotoBase64: String) {
            try {
                val fotoBytes = Base64.decode(fotoBase64, Base64.DEFAULT)
                BovedaPerfil.guardarPerfil(this@MainActivity, nombre, jsonDatos, fotoBytes)
                runOnUiThread {
                    Toast.makeText(this@MainActivity, "Perfil '$nombre' guardado cifrado.", Toast.LENGTH_SHORT).show()
                    webView.evaluateJavascript("window.onPerfilesActualizados && window.onPerfilesActualizados();", null)
                }
            } catch (ex: Exception) {
                runOnUiThread {
                    Toast.makeText(this@MainActivity, "Error al cifrar perfil: ${ex.message}", Toast.LENGTH_LONG).show()
                }
            }
        }

        @JavascriptInterface
        fun desbloquearPerfil(id: String, nombre: String) {
            runOnUiThread {
                autenticarYEjecutar(
                    "Desbloquear perfil: $nombre",
                    "Usa tu huella, rostro o PIN para cargar foto y medidas"
                ) {
                    try {
                        val cargado = BovedaPerfil.cargarPerfil(this@MainActivity, id)
                        if (cargado != null) {
                            val (jsonDatos, fotoBytes) = cargado
                            val fotoB64 = Base64.encodeToString(fotoBytes, Base64.NO_WRAP)
                            val jsonEscapado = JSONObject.quote(jsonDatos)
                            val fotoEscapada = JSONObject.quote(fotoB64)
                            val nombreEscapado = JSONObject.quote(nombre)
                            webView.evaluateJavascript(
                                "window.onPerfilDesbloqueado && window.onPerfilDesbloqueado($jsonEscapado, $fotoEscapada, $nombreEscapado);",
                                null
                            )
                        }
                    } catch (ex: Exception) {
                        Toast.makeText(this@MainActivity, "Error al descifrar: ${ex.message}", Toast.LENGTH_LONG).show()
                    }
                }
            }
        }

        @JavascriptInterface
        fun borrarPerfil(id: String, nombre: String) {
            runOnUiThread {
                autenticarYEjecutar(
                    "Borrar perfil: $nombre",
                    "Confirma con huella o PIN para eliminar este perfil"
                ) {
                    BovedaPerfil.borrarPerfil(this@MainActivity, id)
                    Toast.makeText(this@MainActivity, "Perfil '$nombre' eliminado.", Toast.LENGTH_SHORT).show()
                    webView.evaluateJavascript("window.onPerfilBorrado && window.onPerfilBorrado();", null)
                }
            }
        }

        @JavascriptInterface
        fun consumirPrendaCompartida(): String {
            val b64 = pendingSharedImageBase64 ?: return ""
            val mime = pendingSharedMime
            pendingSharedImageBase64 = null
            return JSONObject()
                .put("imagenBase64", b64)
                .put("mime", mime)
                .toString()
        }

        @JavascriptInterface
        fun listarArmario(perfilId: String): String =
            BovedaPerfil.listarArmario(this@MainActivity, perfilId)

        @JavascriptInterface
        fun guardarPrendaArmario(perfilId: String, jsonMeta: String, imagenBase64: String): String {
            return try {
                val bytes = Base64.decode(imagenBase64, Base64.DEFAULT)
                BovedaPerfil.guardarPrendaArmario(this@MainActivity, perfilId, jsonMeta, bytes)
            } catch (_: Exception) {
                ""
            }
        }

        @JavascriptInterface
        fun cargarPrendaArmario(perfilId: String, prendaId: String): String {
            return try {
                val cargado = BovedaPerfil.cargarPrendaArmario(this@MainActivity, perfilId, prendaId) ?: return ""
                val (meta, bytes) = cargado
                val b64 = Base64.encodeToString(bytes, Base64.NO_WRAP)
                JSONObject()
                    .put("meta", JSONObject(meta))
                    .put("imagenBase64", b64)
                    .toString()
            } catch (_: Exception) {
                ""
            }
        }

        @JavascriptInterface
        fun borrarPrendaArmario(perfilId: String, prendaId: String) {
            BovedaPerfil.borrarPrendaArmario(this@MainActivity, perfilId, prendaId)
        }

        @JavascriptInterface
        fun obtenerCacheTryOn(clave: String): String {
            return try {
                BovedaPerfil.obtenerCacheTryOn(this@MainActivity, clave) ?: ""
            } catch (_: Exception) {
                ""
            }
        }

        @JavascriptInterface
        fun guardarCacheTryOn(clave: String, jsonResultado: String) {
            try {
                BovedaPerfil.guardarCacheTryOn(this@MainActivity, clave, jsonResultado)
            } catch (_: Exception) {
            }
        }

        @JavascriptInterface
        fun limpiarCacheTryOn() {
            BovedaPerfil.limpiarCacheTryOn(this@MainActivity)
            runOnUiThread {
                Toast.makeText(this@MainActivity, "Caché local de pruebas limpiada.", Toast.LENGTH_SHORT).show()
            }
        }

        @JavascriptInterface
        fun exportarPerfil(id: String, nombre: String, password: String) {
            runOnUiThread {
                autenticarYEjecutar(
                    "Exportar respaldo: $nombre",
                    "Confirma con huella o PIN para generar el archivo cifrado"
                ) {
                    try {
                        pendingExportBytes = BovedaPerfil.exportarPerfilCifrado(
                            this@MainActivity,
                            id,
                            nombre,
                            password
                        )
                        val nombreArchivo = "AliLook_${nombre.replace(Regex("[^a-zA-Z0-9_-]"), "_")}.alilook"
                        val intentDoc = Intent(Intent.ACTION_CREATE_DOCUMENT).apply {
                            addCategory(Intent.CATEGORY_OPENABLE)
                            type = "application/octet-stream"
                            putExtra(Intent.EXTRA_TITLE, nombreArchivo)
                        }
                        @Suppress("DEPRECATION")
                        startActivityForResult(intentDoc, REQ_EXPORTAR_PERFIL)
                    } catch (ex: Exception) {
                        pendingExportBytes = null
                        Toast.makeText(this@MainActivity, "Error al exportar: ${ex.message}", Toast.LENGTH_LONG).show()
                    }
                }
            }
        }

        @JavascriptInterface
        fun importarPerfil(password: String) {
            runOnUiThread {
                pendingImportPassword = password
                val intentDoc = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
                    addCategory(Intent.CATEGORY_OPENABLE)
                    type = "*/*"
                }
                @Suppress("DEPRECATION")
                startActivityForResult(intentDoc, REQ_IMPORTAR_PERFIL)
            }
        }
    }

    private fun buscarServidorAutomaticamente() {
        btnBuscar.isEnabled = false
        btnBuscar.text = "Buscando..."
        thread {
            val urlEncontrada = probarUsbLocal() ?: descubrirPorUdp()
            runOnUiThread {
                btnBuscar.isEnabled = true
                btnBuscar.text = "Buscar PC"
                if (urlEncontrada != null) {
                    getSharedPreferences(PREFS_NAME, MODE_PRIVATE)
                        .edit()
                        .putString(KEY_URL, urlEncontrada)
                        .apply()
                    urlInput.setText(urlEncontrada)
                    webView.loadUrl(urlEncontrada)
                    Toast.makeText(this, "Conectado a $urlEncontrada", Toast.LENGTH_SHORT).show()
                } else {
                    Toast.makeText(
                        this,
                        "No se encontró el servidor. Revisa iniciar_servidor.bat y el mismo Wi-Fi.",
                        Toast.LENGTH_LONG
                    ).show()
                }
            }
        }
    }

    private fun probarUsbLocal(): String? {
        return try {
            val conn = (URL("http://127.0.0.1:8000/api/v1/salud").openConnection() as HttpURLConnection).apply {
                connectTimeout = 600
                readTimeout = 600
                requestMethod = "GET"
            }
            val code = conn.responseCode
            conn.disconnect()
            if (code == 200) "http://127.0.0.1:8000" else null
        } catch (_: Exception) {
            null
        }
    }

    private fun descubrirPorUdp(): String? {
        var socket: DatagramSocket? = null
        return try {
            socket = DatagramSocket().apply {
                broadcast = true
                soTimeout = 2500
            }
            val mensaje = "PROYECTO_ALI_DISCOVER".toByteArray()
            val paquete = DatagramPacket(
                mensaje,
                mensaje.size,
                InetAddress.getByName("255.255.255.255"),
                PUERTO_UDP
            )
            socket.send(paquete)

            val buffer = ByteArray(1024)
            val respuesta = DatagramPacket(buffer, buffer.size)
            socket.receive(respuesta)

            val texto = String(respuesta.data, 0, respuesta.length)
            val json = JSONObject(texto)
            if (json.optString("servicio") == "proyecto_ali") {
                val ip = json.optString("ip")
                val puerto = json.optInt("puerto", 8000)
                if (ip.isNotBlank()) "http://$ip:$puerto" else null
            } else {
                null
            }
        } catch (_: Exception) {
            null
        } finally {
            socket?.close()
        }
    }

    private fun solicitarFotoOArchivo() {
        val intentGaleria = Intent(Intent.ACTION_GET_CONTENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            type = "image/*"
        }

        var intentCamara: Intent? = null
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) {
            val archivoFoto = File(cacheDir, "foto_${System.currentTimeMillis()}.jpg")
            camaraUri = FileProvider.getUriForFile(this, "${packageName}.fileprovider", archivoFoto)
            intentCamara = Intent(MediaStore.ACTION_IMAGE_CAPTURE).apply {
                putExtra(MediaStore.EXTRA_OUTPUT, camaraUri)
            }
        }

        val selector = Intent(Intent.ACTION_CHOOSER).apply {
            putExtra(Intent.EXTRA_INTENT, intentGaleria)
            putExtra(Intent.EXTRA_TITLE, "Selecciona o toma una foto")
            if (intentCamara != null) {
                putExtra(Intent.EXTRA_INITIAL_INTENTS, arrayOf(intentCamara))
            }
        }

        startActivityForResult(selector, REQ_ARCHIVO)
    }

    @Deprecated("Deprecated in Java")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        if (requestCode == REQ_EXPORTAR_PERFIL) {
            val bytes = pendingExportBytes
            pendingExportBytes = null
            if (resultCode == RESULT_OK && data?.data != null && bytes != null) {
                try {
                    contentResolver.openOutputStream(data.data!!)?.use { it.write(bytes) }
                    Toast.makeText(this, "Respaldo cifrado exportado correctamente.", Toast.LENGTH_SHORT).show()
                } catch (ex: Exception) {
                    Toast.makeText(this, "Error al guardar respaldo: ${ex.message}", Toast.LENGTH_LONG).show()
                }
            }
            return
        }
        if (requestCode == REQ_IMPORTAR_PERFIL) {
            val password = pendingImportPassword
            pendingImportPassword = null
            if (resultCode == RESULT_OK && data?.data != null && !password.isNullOrEmpty()) {
                try {
                    val bytes = contentResolver.openInputStream(data.data!!)?.use { it.readBytes() }
                        ?: throw IllegalStateException("No se pudo leer el archivo.")
                    val nombre = BovedaPerfil.importarPerfilCifrado(this, bytes, password)
                    Toast.makeText(this, "Perfil '$nombre' importado correctamente.", Toast.LENGTH_SHORT).show()
                    webView.evaluateJavascript("window.onPerfilesActualizados && window.onPerfilesActualizados();", null)
                } catch (ex: Exception) {
                    Toast.makeText(this, "Contraseña incorrecta o archivo inválido.", Toast.LENGTH_LONG).show()
                }
            }
            return
        }
        if (requestCode == REQ_ARCHIVO) {
            val resultados: Array<Uri>? = when {
                resultCode != RESULT_OK -> null
                data?.data != null -> arrayOf(data.data!!)
                camaraUri != null -> arrayOf(camaraUri!!)
                else -> null
            }
            filePathCallback?.onReceiveValue(resultados)
            filePathCallback = null
            return
        }
        super.onActivityResult(requestCode, resultCode, data)
    }
}
