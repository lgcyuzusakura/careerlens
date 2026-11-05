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
        String msg = switch(e.status) { case 400 -> "请检查字段类型和文本长度。"; case 422 -> "材料无法分析，请调整文本。"; case 429 -> "分析繁忙，请稍后重试。"; case 504 -> "下游分析超时。"; default -> "分析服务暂不可用。"; };
        return ResponseEntity.status(e.status).body(new Envelope<>(e.code,msg,null));
    }
    @ExceptionHandler({MethodArgumentNotValidException.class,HttpMessageNotReadableException.class})
    ResponseEntity<Envelope<Void>> invalid(Exception e) { return ResponseEntity.badRequest().body(new Envelope<>("INVALID_INPUT","请检查字段类型和必填内容。",null)); }
    @ExceptionHandler(Exception.class)
    ResponseEntity<Envelope<Void>> unknown(Exception e) { return ResponseEntity.internalServerError().body(new Envelope<>("INTERNAL_ERROR","服务暂不可用。",null)); }
}
