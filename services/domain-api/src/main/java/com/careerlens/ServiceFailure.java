package com.careerlens;

public class ServiceFailure extends RuntimeException {
    public final int status;
    public final String code;
    public ServiceFailure(int status, String code) { super(code); this.status = status; this.code = code; }
}
