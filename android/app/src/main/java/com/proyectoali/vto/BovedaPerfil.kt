package com.proyectoali.vto

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.DataInputStream
import java.io.DataOutputStream
import java.io.File
import java.security.KeyStore
import java.security.MessageDigest
import java.security.SecureRandom
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.SecretKeyFactory
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.PBEKeySpec
import javax.crypto.spec.SecretKeySpec

/**
 * Almacena múltiples perfiles familiares (nombre, foto y medidas) cifrados con AES-256-GCM
 * usando una clave no exportable del Android Keystore.
 */
object BovedaPerfil {

    private const val KEYSTORE_PROVIDER = "AndroidKeyStore"
    private const val ALIAS_CLAVE = "ProyectoAliPerfilKey"
    private const val CARPETA_PERFILES = "perfiles_cifrados"
    private const val CARPETA_ARMARIO = "armario_cifrado"
    private const val CARPETA_CACHE = "cache_tryon_cifrado"
    private const val PREFS_INDICE = "proyecto_ali_indice_perfiles"
    private const val PREFS_ARMARIO = "proyecto_ali_indice_armario"
    private const val PREFS_CACHE = "proyecto_ali_cache_tryon"
    private const val KEY_INDICE = "lista_perfiles"
    private const val KEY_ULTIMO_PERFIL_ID = "ultimo_perfil_id"
    private const val KEY_ULTIMO_PERFIL_NOMBRE = "ultimo_perfil_nombre"
    private const val KEY_CACHE_ORDEN = "orden_cache"
    private const val MAX_CACHE_TRYON = 20
    private const val TRANSFORMACION = "AES/GCM/NoPadding"
    private const val IV_LEN = 12
    private const val TAG_BITS = 128

    private fun obtenerOCrearClave(): SecretKey {
        val ks = KeyStore.getInstance(KEYSTORE_PROVIDER).apply { load(null) }
        val existente = ks.getKey(ALIAS_CLAVE, null) as? SecretKey
        if (existente != null) return existente

        val keyGen = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, KEYSTORE_PROVIDER)
        val spec = KeyGenParameterSpec.Builder(
            ALIAS_CLAVE,
            KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT
        )
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setKeySize(256)
            .build()
        keyGen.init(spec)
        return keyGen.generateKey()
    }

    private fun carpeta(context: Context): File {
        return File(context.filesDir, CARPETA_PERFILES).apply {
            if (!exists()) mkdirs()
        }
    }

    private fun idDesdeNombre(nombre: String): String {
        val digest = MessageDigest.getInstance("SHA-256")
            .digest(nombre.trim().lowercase().toByteArray(Charsets.UTF_8))
        return digest.take(12).joinToString("") { "%02x".format(it) }
    }

    private fun leerIndice(context: Context): JSONArray {
        val prefs = context.getSharedPreferences(PREFS_INDICE, Context.MODE_PRIVATE)
        val raw = prefs.getString(KEY_INDICE, "[]") ?: "[]"
        return try {
            JSONArray(raw)
        } catch (_: Exception) {
            JSONArray()
        }
    }

    private fun guardarIndice(context: Context, arr: JSONArray) {
        context.getSharedPreferences(PREFS_INDICE, Context.MODE_PRIVATE)
            .edit()
            .putString(KEY_INDICE, arr.toString())
            .apply()
    }

    fun listarPerfiles(context: Context): String {
        val indice = leerIndice(context)
        val vigentes = JSONArray()
        val dir = carpeta(context)
        for (i in 0 until indice.length()) {
            val obj = indice.getJSONObject(i)
            val id = obj.optString("id")
            if (id.isNotBlank() && File(dir, "$id.enc").exists()) {
                vigentes.put(obj)
            }
        }
        return vigentes.toString()
    }

    fun guardarUltimoPerfil(context: Context, id: String, nombre: String) {
        context.getSharedPreferences(PREFS_INDICE, Context.MODE_PRIVATE)
            .edit()
            .putString(KEY_ULTIMO_PERFIL_ID, id)
            .putString(KEY_ULTIMO_PERFIL_NOMBRE, nombre)
            .apply()
    }

    fun obtenerUltimoPerfil(context: Context): String {
        val prefs = context.getSharedPreferences(PREFS_INDICE, Context.MODE_PRIVATE)
        val id = prefs.getString(KEY_ULTIMO_PERFIL_ID, "") ?: ""
        val nombre = prefs.getString(KEY_ULTIMO_PERFIL_NOMBRE, "") ?: ""
        if (id.isBlank() || !File(carpeta(context), "$id.enc").exists()) return ""
        return JSONObject().put("id", id).put("nombre", nombre).toString()
    }

    fun borrarPerfil(context: Context, id: String) {
        val archivo = File(carpeta(context), "$id.enc")
        if (archivo.exists()) archivo.delete()

        val prefs = context.getSharedPreferences(PREFS_INDICE, Context.MODE_PRIVATE)
        if (prefs.getString(KEY_ULTIMO_PERFIL_ID, "") == id) {
            prefs.edit().remove(KEY_ULTIMO_PERFIL_ID).remove(KEY_ULTIMO_PERFIL_NOMBRE).apply()
        }

        val indice = leerIndice(context)
        val nuevo = JSONArray()
        for (i in 0 until indice.length()) {
            val obj = indice.getJSONObject(i)
            if (obj.optString("id") != id) {
                nuevo.put(obj)
            }
        }
        guardarIndice(context, nuevo)
    }

    private fun cifrarBytes(plano: ByteArray): ByteArray {
        val cipher = Cipher.getInstance(TRANSFORMACION)
        cipher.init(Cipher.ENCRYPT_MODE, obtenerOCrearClave())
        val iv = cipher.iv
        val cifrado = cipher.doFinal(plano)
        return iv + cifrado
    }

    private fun descifrarBytes(contenido: ByteArray): ByteArray? {
        if (contenido.size <= IV_LEN) return null
        val iv = contenido.copyOfRange(0, IV_LEN)
        val cifrado = contenido.copyOfRange(IV_LEN, contenido.size)
        val cipher = Cipher.getInstance(TRANSFORMACION)
        cipher.init(Cipher.DECRYPT_MODE, obtenerOCrearClave(), GCMParameterSpec(TAG_BITS, iv))
        return cipher.doFinal(cifrado)
    }

    private fun empaquetarPayload(json: String, imagenBytes: ByteArray): ByteArray {
        val payloadStream = ByteArrayOutputStream()
        DataOutputStream(payloadStream).use { dos ->
            val datosBytes = json.toByteArray(Charsets.UTF_8)
            dos.writeInt(datosBytes.size)
            dos.write(datosBytes)
            dos.writeInt(imagenBytes.size)
            dos.write(imagenBytes)
        }
        return payloadStream.toByteArray()
    }

    private fun desempaquetarPayload(plano: ByteArray): Pair<String, ByteArray> {
        DataInputStream(ByteArrayInputStream(plano)).use { dis ->
            val lenDatos = dis.readInt()
            val datosBytes = ByteArray(lenDatos)
            dis.readFully(datosBytes)
            val lenFoto = dis.readInt()
            val fotoBytes = ByteArray(lenFoto)
            dis.readFully(fotoBytes)
            return Pair(String(datosBytes, Charsets.UTF_8), fotoBytes)
        }
    }

    fun guardarPerfil(context: Context, nombre: String, jsonDatos: String, fotoBytes: ByteArray): String {
        val nombreLimpio = nombre.trim().ifEmpty { "Principal" }
        val id = idDesdeNombre(nombreLimpio)

        val cifrado = cifrarBytes(empaquetarPayload(jsonDatos, fotoBytes))
        File(carpeta(context), "$id.enc").writeBytes(cifrado)

        val indice = leerIndice(context)
        val nuevo = JSONArray()
        for (i in 0 until indice.length()) {
            val obj = indice.getJSONObject(i)
            if (obj.optString("id") != id) {
                nuevo.put(obj)
            }
        }
        nuevo.put(JSONObject().put("id", id).put("nombre", nombreLimpio))
        guardarIndice(context, nuevo)
        guardarUltimoPerfil(context, id, nombreLimpio)
        return id
    }

    fun cargarPerfil(context: Context, id: String): Pair<String, ByteArray>? {
        val archivo = File(carpeta(context), "$id.enc")
        if (!archivo.exists()) return null
        val plano = descifrarBytes(archivo.readBytes()) ?: return null
        val res = desempaquetarPayload(plano)
        val indice = leerIndice(context)
        var nombre = ""
        for (i in 0 until indice.length()) {
            val obj = indice.getJSONObject(i)
            if (obj.optString("id") == id) {
                nombre = obj.optString("nombre")
                break
            }
        }
        if (nombre.isNotBlank()) guardarUltimoPerfil(context, id, nombre)
        return res
    }

    // --- Armario Digital cifrado por perfil ---

    private fun perfilSeguro(perfilId: String): String {
        val limpio = perfilId.trim().replace(Regex("[^a-zA-Z0-9_-]"), "")
        return limpio.ifEmpty { "predeterminado" }
    }

    private fun carpetaArmario(context: Context, perfilId: String): File {
        val base = File(context.filesDir, CARPETA_ARMARIO)
        return File(base, perfilSeguro(perfilId)).apply {
            if (!exists()) mkdirs()
        }
    }

    private fun leerIndiceArmario(context: Context, perfilId: String): JSONArray {
        val prefs = context.getSharedPreferences(PREFS_ARMARIO, Context.MODE_PRIVATE)
        val raw = prefs.getString("armario_${perfilSeguro(perfilId)}", "[]") ?: "[]"
        return try {
            JSONArray(raw)
        } catch (_: Exception) {
            JSONArray()
        }
    }

    private fun guardarIndiceArmario(context: Context, perfilId: String, arr: JSONArray) {
        context.getSharedPreferences(PREFS_ARMARIO, Context.MODE_PRIVATE)
            .edit()
            .putString("armario_${perfilSeguro(perfilId)}", arr.toString())
            .apply()
    }

    fun listarArmario(context: Context, perfilId: String): String {
        val indice = leerIndiceArmario(context, perfilId)
        val vigentes = JSONArray()
        val dir = carpetaArmario(context, perfilId)
        for (i in 0 until indice.length()) {
            val obj = indice.getJSONObject(i)
            val id = obj.optString("id")
            if (id.isNotBlank() && File(dir, "$id.enc").exists()) {
                vigentes.put(obj)
            }
        }
        return vigentes.toString()
    }

    fun guardarPrendaArmario(
        context: Context,
        perfilId: String,
        jsonMeta: String,
        imagenBytes: ByteArray
    ): String {
        val metaObj = try {
            JSONObject(jsonMeta)
        } catch (_: Exception) {
            JSONObject()
        }
        val id = metaObj.optString("id").ifBlank {
            "p_${System.currentTimeMillis()}_${(1000..9999).random()}"
        }
        metaObj.put("id", id)

        val cifrado = cifrarBytes(empaquetarPayload(metaObj.toString(), imagenBytes))
        File(carpetaArmario(context, perfilId), "$id.enc").writeBytes(cifrado)

        val indice = leerIndiceArmario(context, perfilId)
        val nuevo = JSONArray()
        nuevo.put(metaObj)
        for (i in 0 until indice.length()) {
            val obj = indice.getJSONObject(i)
            if (obj.optString("id") != id) {
                nuevo.put(obj)
            }
        }
        guardarIndiceArmario(context, perfilId, nuevo)
        return id
    }

    fun cargarPrendaArmario(context: Context, perfilId: String, prendaId: String): Pair<String, ByteArray>? {
        val archivo = File(carpetaArmario(context, perfilId), "$prendaId.enc")
        if (!archivo.exists()) return null
        val plano = descifrarBytes(archivo.readBytes()) ?: return null
        return desempaquetarPayload(plano)
    }

    fun borrarPrendaArmario(context: Context, perfilId: String, prendaId: String) {
        val archivo = File(carpetaArmario(context, perfilId), "$prendaId.enc")
        if (archivo.exists()) archivo.delete()

        val indice = leerIndiceArmario(context, perfilId)
        val nuevo = JSONArray()
        for (i in 0 until indice.length()) {
            val obj = indice.getJSONObject(i)
            if (obj.optString("id") != prendaId) {
                nuevo.put(obj)
            }
        }
        guardarIndiceArmario(context, perfilId, nuevo)
    }

    // --- Caché local cifrada de resultados Try-On ---

    private fun claveCacheSegura(clave: String): String {
        return clave.trim().replace(Regex("[^a-zA-Z0-9_-]"), "").take(64).ifEmpty { "default" }
    }

    private fun carpetaCache(context: Context): File {
        return File(context.filesDir, CARPETA_CACHE).apply {
            if (!exists()) mkdirs()
        }
    }

    fun guardarCacheTryOn(context: Context, clave: String, jsonResultado: String) {
        val claveLimpia = claveCacheSegura(clave)
        val cifrado = cifrarBytes(jsonResultado.toByteArray(Charsets.UTF_8))
        val dir = carpetaCache(context)
        File(dir, "$claveLimpia.enc").writeBytes(cifrado)

        val prefs = context.getSharedPreferences(PREFS_CACHE, Context.MODE_PRIVATE)
        val raw = prefs.getString(KEY_CACHE_ORDEN, "[]") ?: "[]"
        val arr = try { JSONArray(raw) } catch (_: Exception) { JSONArray() }
        val nuevo = JSONArray()
        nuevo.put(claveLimpia)
        for (i in 0 until arr.length()) {
            val item = arr.optString(i)
            if (item.isNotBlank() && item != claveLimpia) {
                nuevo.put(item)
            }
        }
        val recortado = JSONArray()
        for (i in 0 until nuevo.length()) {
            val item = nuevo.getString(i)
            if (i < MAX_CACHE_TRYON) {
                recortado.put(item)
            } else {
                File(dir, "$item.enc").delete()
            }
        }
        prefs.edit().putString(KEY_CACHE_ORDEN, recortado.toString()).apply()
    }

    fun obtenerCacheTryOn(context: Context, clave: String): String? {
        val claveLimpia = claveCacheSegura(clave)
        val archivo = File(carpetaCache(context), "$claveLimpia.enc")
        if (!archivo.exists()) return null
        val plano = descifrarBytes(archivo.readBytes()) ?: return null
        return String(plano, Charsets.UTF_8)
    }

    fun limpiarCacheTryOn(context: Context) {
        val dir = carpetaCache(context)
        dir.listFiles()?.forEach { it.delete() }
        context.getSharedPreferences(PREFS_CACHE, Context.MODE_PRIVATE)
            .edit()
            .remove(KEY_CACHE_ORDEN)
            .apply()
    }

    // --- Exportación e importación portátil cifrada con contraseña (.alilook) ---

    private val CABECERA_RESPALDO = "ALILOOK1".toByteArray(Charsets.US_ASCII)
    private const val SALT_LEN = 16
    private const val PBKDF2_ITERACIONES = 120_000

    private fun derivarClaveDesdePassword(password: String, salt: ByteArray): SecretKey {
        val factory = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256")
        val spec = PBEKeySpec(password.toCharArray(), salt, PBKDF2_ITERACIONES, 256)
        val raw = factory.generateSecret(spec).encoded
        return SecretKeySpec(raw, "AES")
    }

    fun exportarPerfilCifrado(
        context: Context,
        perfilId: String,
        nombre: String,
        password: String
    ): ByteArray {
        require(password.length >= 4) { "La contraseña debe tener al menos 4 caracteres." }
        val cargado = cargarPerfil(context, perfilId)
            ?: throw IllegalStateException("No se encontró el perfil '$nombre'.")
        val (jsonDatos, fotoBytes) = cargado

        val prendasArr = JSONArray()
        val listaArmario = JSONArray(listarArmario(context, perfilId))
        for (i in 0 until listaArmario.length()) {
            val meta = listaArmario.getJSONObject(i)
            val prendaId = meta.optString("id")
            val prendaCargada = cargarPrendaArmario(context, perfilId, prendaId)
            if (prendaCargada != null) {
                val (metaStr, imgBytes) = prendaCargada
                prendasArr.put(
                    JSONObject()
                        .put("meta", JSONObject(metaStr))
                        .put("imagen_base64", Base64.encodeToString(imgBytes, Base64.NO_WRAP))
                )
            }
        }

        val paqueteJson = JSONObject()
            .put("version_formato", 1)
            .put("nombre", nombre)
            .put("datos", JSONObject(jsonDatos))
            .put("foto_base64", Base64.encodeToString(fotoBytes, Base64.NO_WRAP))
            .put("armario", prendasArr)
            .toString()

        val salt = ByteArray(SALT_LEN).also { SecureRandom().nextBytes(it) }
        val clave = derivarClaveDesdePassword(password, salt)
        val cipher = Cipher.getInstance(TRANSFORMACION)
        cipher.init(Cipher.ENCRYPT_MODE, clave)
        val iv = cipher.iv
        val cifrado = cipher.doFinal(paqueteJson.toByteArray(Charsets.UTF_8))

        val salida = ByteArrayOutputStream()
        salida.write(CABECERA_RESPALDO)
        salida.write(salt)
        salida.write(iv)
        salida.write(cifrado)
        return salida.toByteArray()
    }

    fun importarPerfilCifrado(
        context: Context,
        paqueteBytes: ByteArray,
        password: String
    ): String {
        val minimo = CABECERA_RESPALDO.size + SALT_LEN + IV_LEN + 16
        require(paqueteBytes.size >= minimo) { "El archivo de respaldo no es válido o está dañado." }

        val cabecera = paqueteBytes.copyOfRange(0, CABECERA_RESPALDO.size)
        require(cabecera.contentEquals(CABECERA_RESPALDO)) { "Formato de respaldo no reconocido." }

        var pos = CABECERA_RESPALDO.size
        val salt = paqueteBytes.copyOfRange(pos, pos + SALT_LEN)
        pos += SALT_LEN
        val iv = paqueteBytes.copyOfRange(pos, pos + IV_LEN)
        pos += IV_LEN
        val cifrado = paqueteBytes.copyOfRange(pos, paqueteBytes.size)

        val clave = derivarClaveDesdePassword(password, salt)
        val cipher = Cipher.getInstance(TRANSFORMACION)
        cipher.init(Cipher.DECRYPT_MODE, clave, GCMParameterSpec(TAG_BITS, iv))
        val plano = cipher.doFinal(cifrado)

        val raiz = JSONObject(String(plano, Charsets.UTF_8))
        val nombre = raiz.optString("nombre").ifBlank { "Importado" }
        val datosStr = raiz.getJSONObject("datos").toString()
        val fotoBytes = Base64.decode(raiz.getString("foto_base64"), Base64.DEFAULT)

        val nuevoPerfilId = guardarPerfil(context, nombre, datosStr, fotoBytes)
        val armario = raiz.optJSONArray("armario") ?: JSONArray()
        for (i in 0 until armario.length()) {
            val item = armario.getJSONObject(i)
            val metaStr = item.getJSONObject("meta").toString()
            val imgBytes = Base64.decode(item.getString("imagen_base64"), Base64.DEFAULT)
            guardarPrendaArmario(context, nuevoPerfilId, metaStr, imgBytes)
        }
        return nombre
    }
}
