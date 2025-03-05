module ex(clock,a);
   input clock,a;
   reg 	 s0,s1;
   wire  b,ns0,ns1;
   and g0(b,a,s0);
   not g1(ns0,b);
   not g2(ns1,s1);
   always @(posedge clock) begin
      s0<=ns0;
      s1<=ns1;
   end
endmodule

