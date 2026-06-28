package com.smarthr.util;

import com.smarthr.exception.GlobalException;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.io.InputStream;
import java.util.Locale;
import java.util.Set;

/**
 * 上传文件安全校验：扩展名白名单 + 文件头魔数校验。
 *
 * <p>仅靠扩展名或客户端声明的 Content-Type 都可被伪造，这里在落盘前同时校验扩展名白名单
 * 与文件头魔数（magic bytes），阻止把可执行/脚本文件伪装成 pdf/docx 上传。文本类（txt/md）
 * 无稳定魔数，按扩展名白名单放行。
 */
public final class FileUploadValidator {

    private FileUploadValidator() {
    }

    // 各业务可复用的扩展名白名单。
    public static final Set<String> RESUME_EXTENSIONS = Set.of("pdf", "docx");
    public static final Set<String> KNOWLEDGE_EXTENSIONS = Set.of("pdf", "docx", "doc", "txt", "md");

    private static final byte[] MAGIC_PDF = {0x25, 0x50, 0x44, 0x46};                 // %PDF
    private static final byte[] MAGIC_ZIP = {0x50, 0x4B, 0x03, 0x04};                 // PK..（docx 是 zip）
    private static final byte[] MAGIC_OLE2 = {(byte) 0xD0, (byte) 0xCF, 0x11, (byte) 0xE0,
            (byte) 0xA1, (byte) 0xB1, 0x1A, (byte) 0xE1};                             // 旧版 .doc OLE2

    /**
     * 校验上传文件。不合规时抛出 {@link GlobalException}(400)，由全局异常处理器统一返回。
     *
     * @param file              上传文件
     * @param allowedExtensions 允许的扩展名集合（小写、不含点）
     */
    public static void validate(MultipartFile file, Set<String> allowedExtensions) {
        if (file == null || file.isEmpty()) {
            throw new GlobalException(400, "上传文件为空");
        }

        String originalFilename = file.getOriginalFilename();
        if (originalFilename == null || originalFilename.isBlank()) {
            throw new GlobalException(400, "文件名为空");
        }

        String extension = extensionOf(originalFilename);
        if (extension.isEmpty() || !allowedExtensions.contains(extension)) {
            throw new GlobalException(400, "不支持的文件类型，仅允许：" + allowedExtensions);
        }

        byte[] head = readHead(file);
        if (!magicMatches(extension, head)) {
            throw new GlobalException(400, "文件内容与扩展名不符（疑似伪装文件）：." + extension);
        }
    }

    private static String extensionOf(String filename) {
        int dot = filename.lastIndexOf('.');
        if (dot < 0 || dot == filename.length() - 1) {
            return "";
        }
        return filename.substring(dot + 1).toLowerCase(Locale.ROOT);
    }

    private static byte[] readHead(MultipartFile file) {
        // 每次 getInputStream() 都是基于已存内容的新流，读取文件头不会影响后续读取。
        try (InputStream in = file.getInputStream()) {
            byte[] head = new byte[8];
            int read = in.readNBytes(head, 0, head.length);
            if (read <= 0) {
                throw new GlobalException(400, "上传文件内容为空");
            }
            if (read < head.length) {
                byte[] trimmed = new byte[read];
                System.arraycopy(head, 0, trimmed, 0, read);
                return trimmed;
            }
            return head;
        } catch (IOException e) {
            throw new GlobalException(400, "读取上传文件失败：" + e.getMessage());
        }
    }

    private static boolean magicMatches(String extension, byte[] head) {
        switch (extension) {
            case "pdf":
                return startsWith(head, MAGIC_PDF);
            case "docx":
                return startsWith(head, MAGIC_ZIP);
            case "doc":
                // 旧版 .doc 为 OLE2；部分由 docx 误命名的也可能是 zip，这里两者均接受。
                return startsWith(head, MAGIC_OLE2) || startsWith(head, MAGIC_ZIP);
            case "txt":
            case "md":
                // 纯文本无稳定魔数，按扩展名白名单放行。
                return true;
            default:
                return false;
        }
    }

    private static boolean startsWith(byte[] data, byte[] prefix) {
        if (data.length < prefix.length) {
            return false;
        }
        for (int i = 0; i < prefix.length; i++) {
            if (data[i] != prefix[i]) {
                return false;
            }
        }
        return true;
    }
}
