package com.careerlens;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.http.converter.HttpMessageNotReadableException;
import static com.careerlens.Models.*;

@RestControllerAdvice
public class Errors {
    @ExceptionHandler(ServiceFailure.class)
    ResponseEntity<Envelope<Void>> failure(ServiceFailure e) {
        String msg = switch(e.status) { case 400 -> "请检查字段类型和文本长度。"; case 401 -> "账号或密码不正确，请重新登录。"; case 402 -> "可用额度不足，请前往账户页。"; case 403 -> "需要管理员权限。"; case 404 -> "记录不存在。"; case 409 -> "记录冲突，请检查用户名、余额或重复请求。"; case 413 -> "文件过大，最多 2 MiB。"; case 422 -> "材料无法解析，请使用可复制文字的文本或 PDF。"; case 429 -> "分析繁忙，请稍后重试。"; case 504 -> "下游分析超时。"; default -> "分析服务暂不可用。"; };
        return ResponseEntity.status(e.status).body(new Envelope<>(e.code,msg,null));
    }
    @ExceptionHandler({MethodArgumentNotValidException.class,HttpMessageNotReadableException.class})
    ResponseEntity<Envelope<Void>> invalid(Exception e) { return ResponseEntity.badRequest().body(new Envelope<>("INVALID_INPUT","请检查字段类型和必填内容。",null)); }
    @ExceptionHandler({org.springframework.web.servlet.resource.NoResourceFoundException.class, org.springframework.web.HttpRequestMethodNotSupportedException.class, org.springframework.web.HttpMediaTypeNotSupportedException.class})
    ResponseEntity<Envelope<Void>> routing(Exception e) {
        int status = ((org.springframework.web.ErrorResponse)e).getStatusCode().value();
        String code = switch(status) { case 404 -> "NOT_FOUND"; case 405 -> "METHOD_NOT_ALLOWED"; default -> "UNSUPPORTED_MEDIA_TYPE"; };
        return ResponseEntity.status(status).body(new Envelope<>(code,"请求的资源、方法或内容类型不支持。",null));
    }
    @ExceptionHandler(Exception.class)
    ResponseEntity<Envelope<Void>> unknown(Exception e) { return ResponseEntity.internalServerError().body(new Envelope<>("INTERNAL_ERROR","服务暂不可用。",null)); }
}
