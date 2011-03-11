      SUBROUTINE HISTOGRAM2D(N,X,Y,Z,NXBINS,NYBINS,XLIM,YLIM,DX,DY,
     1  NST,HST)

Cf2py intent(in) n
Cf2py intent(in) x
Cf2py depend(n) x
Cf2py intent(in) y
Cf2py depend(n) y
Cf2py intent(in) z
Cf2py depend(n) z
Cf2py intent(in) nxbins
Cf2py intent(in) nybins
Cf2py intent(in) xlim       
Cf2py intent(in) ylim
Cf2py intent(in) dx
Cf2py intent(in) dy
Cf2py intent(in,out) nst
Cf2py depend(nxbins,nybins) nst
Cf2py intent(in,out) hst
Cf2py depend(nxbins,nybins) hst

      IMPLICIT NONE
      INTEGER*4   N
      REAL*4      X(0:N-1),Y(0:N-1),Z(0:N-1)
      INTEGER*8   NXBINS,NYBINS
      REAL*8      XLIM(0:1),YLIM(0:1)
      REAL*4      NST(0:NXBINS-1,0:NYBINS-1)
      REAL*4      HST(0:NXBINS-1,0:NYBINS-1)

      INTEGER*4   I,J,K
      REAL*8      DX,DY


      DO K=0,N
        IF ( ( X(K) .GE. XLIM(0) .AND. X(K) .LE. XLIM(1)) .AND.
     1    (Y(K) .GE. YLIM(0) .AND. Y(K). LE. YLIM(1)) ) THEN
          I = INT((X(K)-XLIM(0))/DX)
          J = INT((Y(K)-YLIM(0))/DY)
          IF ( (I .GE. 0 .AND. I .LT. NXBINS) .AND.
     1       (J .GE. 0 .AND. J .LT. NYBINS) ) THEN
            NST(I,J) = NST(I,J)+1.0
            HST(I,J) = HST(I,J)+Z(K)
          END IF
        END IF
      END DO
      RETURN
      END