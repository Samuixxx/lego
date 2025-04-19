"""

Nome: MotorUtils

Descrizione:
Modulo per la gestione del motore LEGO tramite PiStorms.
Questo modulo fornisce una classe `MotorUtils` per controllare un motore LEGO, gestire il movimento 
avanti e indietro, la rotazione e la velocità. Supporta anche la gestione del movimento in parallelo, 
con funzionalità per la sterzata progressiva e il fermo graduale del motore. Le comunicazioni con il 
client avvengono tramite WebSocket, consentendo il controllo remoto del motore.

Dipendenze:
- asyncio per la gestione delle operazioni asincrone.
- json per la gestione della comunicazione dei dati tramite WebSocket.
- utils.motor.motorenums per le definizioni di direzione, sterzata, velocità e controlli di sterzata.

Autore: Zs
Data di Creazione: 02-04-2025
"""

import asyncio
import json
import websockets
import time
import websockets
import logging
from utils.motor.motorenums.direction import Direction
from utils.motor.motorenums.turn import Turn
from utils.motor.motorenums.speed_controls import SpeedControls
from utils.motor.motorenums.turn_controls import TurnControls
from utils.motor.motorenums.gears import Gear


class MotorUtils:
    """
    Classe per la gestione del motore LEGO tramite PiStorms.

    Attributes:
        websocket (WebSocket): Connessione WebSocket per inviare aggiornamenti.
        _is_started (bool): Indica lo stato di accensione/spegnimento del motore del LEGO
        __motor_1 (oggetto): Rappresenta il primo motore fisico usato per far avanzare o retrocedere il LEGO.
        __motor_2 (oggetto): Rappresenta il secondo motore fisico usato per far avanzare o retrocedere il LEGO.
        __turn_motor (oggetto): Rappresenta il terzo motore fisico usato per far sterzare il LEGO.
        _move_speed (int): Velocità attuale del motore.
        _turn_angle (int): Indica l'angolo di rotazione del motore.
        _is_moving (bool): Indica se il motore è in movimento.
        _is_turning (bool): Indica se il motore è in rotazione.
        _UPDATE_VELOCITY_TIME_OFFSET (int): Indica il tempo di attesa per ogni ciclo nei metodi _turn e _unturn.
    """

    def __init__(self, websocket):
        """
        Inizializza la classe MotorUtils con il WebSocket e le variabili di stato.

        Args:
            websocket (WebSocket): Connessione WebSocket per la comunicazione con il client.
        """
        # from PiStorms import PiStorms
        self.websocket = websocket 
        self._is_started = False 
        self._last_activation = None 
        # self._psm = PiStorms()   
        # self.__motor_1 = self._psm.BAM1
        # self.__motor_2 = self._psm.BAM2
        # self.__turn_motor = self._psm.BBM1
        self._motor_gear = Gear.NEUTRAL 
        self._turbo_value = 0
        self._brake_intensity = 1
        self._move_speed = 0  
        self._turn_angle = 0 
        self._is_moving = False  
        self._is_turning = False  
        self._UPDATE_VELOCITY_TIME_OFFSET = 0.3

    async def toggle_motor_status(self) -> None:
        """
        Inverte lo stato del motore in risposta a una richiesta del client.

        Se il motore è attivo, viene spento e viene calcolato il tempo di attivazione
        dell'ultimo intervallo. Se è spento, viene attivato e il tempo viene azzerato.

        Returns:
            None
        """
        current_time = time.time()

        activation_time = None
        if self._is_started:
            activation_time = current_time - self._last_activation
            self._last_activation = None
        else:
            self._last_activation = current_time

        self._is_started = not self._is_started

        try:
            if self.websocket and activation_time is not None and hasattr(self, '_max_speed_reached'):
                await self.websocket.send(json.dumps({
                    "ok": True,
                    "activationTime": activation_time,
                    "maxSpeed": self._max_speed_reached
                }))
        except websockets.exceptions.ConnectionClosedError:
            logging.error("WebSocket connection closed unexpectedly.")
        except Exception as e:
            logging.error(f"An error occurred while sending data via WebSocket: {e}")

    def get_motor_status(self) -> bool:
        """
        Restituisce lo stato booleano dei motori.

        Returns:
            bool: True se i motori sono attivi, False altrimenti.
        """
        return self._is_started
    
    async def turn(self, side: Turn, delay: float = 0.2, turn_increment: int = 1) -> None:
        """ 
        Regola progressivamente l'angolo di sterzata per girare a sinistra o a destra.  
        - Se è già in corso una sterzata, la funzione esce immediatamente per evitare esecuzioni multiple.  
        - Modifica l'angolo di sterzata incrementandolo/decrementandolo progressivamente fino al massimo consentito.  
        - Interrompe l'incremento se il tasto viene rilasciato (`_stop_turning` diventa `True`).  
        - Invia l'angolo aggiornato al client tramite WebSocket.  
        - Si assicura di non inviare dati ridondanti se l'angolo non cambia.  

        Args:  
        - `side` (Turn): Direzione della sterzata (sinistra o destra).  
        - `delay` (float, default 0.2): Ritardo tra gli incrementi dell'angolo.  
        - `turn_increment` (int, default 1): Incremento dell'angolo ad ogni iterazione.  

        Returns:
            None
        """

        if not self._is_started:
            return

        self._is_turning = True
        self._stop_turning = False
        turn_increment = -turn_increment if side == Turn.LEFT else turn_increment
        max_angle = TurnControls.MAXIMUM_TURN_ANGLE.value

        while not self._stop_turning and self._turn_angle != max_angle:
            new_angle = self._turn_angle + turn_increment
            new_angle = max(-max_angle, min(new_angle, max_angle))

            if new_angle == self._turn_angle:
                break

            self._turn_angle = new_angle

            # Controllo del motore di sterzo (opzionale)
            # self.__turn_motor.runDegs(degs=turn_increment, speed=TurnControls.TURN_VELOCITY.value)

            try:
                await self.websocket.send(json.dumps({
                    "ok": True,
                    "motorangle": self._turn_angle,
                    "direction": "left" if side == Turn.LEFT else "right"
                }))
            except Exception as e:
                print(f"Errore durante l'invio dei dati al client: {e}")

            await asyncio.sleep(delay=delay)

        self._is_turning = False

    async def unturn(self, delay: float = 0.2) -> None:
        """
        Gradualmente riporta l'angolo di rotazione (`self._turn_angle`) a 0.

        Se l'angolo è già 0, la funzione termina immediatamente. Altrimenti,
        decrementa o incrementa l'angolo di 1 unità alla volta, a seconda del
        segno dell'angolo corrente. Dopo ogni modifica, invia l'angolo aggiornato
        al client tramite il websocket.

        La funzione utilizza `asyncio.sleep(0.1)` per introdurre una pausa tra
        ogni aggiornamento dell'angolo, permettendo una transizione graduale.

        Una volta che l'angolo raggiunge 0, invia un messaggio finale al client
        con l'angolo impostato a 0.

        Stampa messaggi di debug per indicare quando l'angolo è già 0 e quando
        è stato riportato a 0.

        Returns:
            None
        """
        if not self._is_started:
            return  # Evita esecuzioni se il motore non è acceso
        
        if self._turn_angle == 0:
            return  # Esci immediatamente se già a zero
        
        self._stop_turning = True
        self._is_turning = True

        turn_increment = 1 if self._turn_angle > 0 else -1

        while self._turn_angle != 0:
            # Decremento o incremento progressivamente l'angolo
            if abs(self._turn_angle) <= abs(turn_increment):
                is_last_step = True
                self._turn_angle = 0
            else:
                self._turn_angle -= turn_increment

            """
            self.__turn_motor.runDegs(degs=turn_increment, speed=TurnControls.TURN_VELOCITY.value, brakeOnCompletion=is_last_step)
            """
            # Invia l'angolo aggiornato al client
            await self.websocket.send(json.dumps({
                "ok": True,
                "motorangle": self._turn_angle,
                "straightening": True
                }))
            
            await asyncio.sleep(delay=delay)
        
        self._is_turning = False
    
    async def move_forward(self) -> None:
        """
        Avvia il movimento del motore in avanti, incrementando automaticamente la velocità fino al limite massimo.

        La funzione controlla se la marcia corrente consente il movimento in avanti.
        Se sì, attiva il movimento e inizia ad aumentare gradualmente la velocità a intervalli regolari,
        fino a raggiungere il valore massimo consentito per la marcia attuale, eventualmente maggiorato dal valore turbo.

        Durante ogni incremento, viene inviato un messaggio tramite WebSocket contenente la velocità attuale
        e la velocità massima raggiunta fino a quel momento.

        Returns:
            None
        """

        if self._motor_gear not in {Gear.FIRST.value, Gear.SECOND.value, Gear.THIRD.value, Gear.FOURTH.value}:
            return

        self._is_moving = True
        max_speed = SpeedControls.MAXIMUM_PER_GEAR.value * int(self._motor_gear) + self._turbo_value

        while self._move_speed < max_speed and self._move_speed < SpeedControls.MAXIMUM_VALOCITY_FORWARD.value:
            self._move_speed += 1

            if not hasattr(self, '_max_speed_reached') or self._move_speed > self._max_speed_reached:
                self._max_speed_reached = self._move_speed

            try:
                await self.websocket.send(json.dumps({
                    "ok": True,
                    "motorspeed": self._move_speed,
                    "direction": "forward"
                }))
            except Exception as e:
                print(f"[ERRORE] WebSocket non ha inviato il dato: {e}")

            await asyncio.sleep(self._UPDATE_VELOCITY_TIME_OFFSET)


    async def move_backward(self) -> None:
        """
        Metodo responsabile della retromarcia del veicolo
        Decrementa gradualmente la velocità entro il limite per la retromarcia
        
        Returns:
            int: Velocità attuale dopo l'aggiornamento.
        """

        if self._motor_gear != Gear.RETRO.value: # controllo che la marcia sia inserita in retro sennò non eseguo niente
            return

        self._is_moving = True
        
        while self._move_speed > -SpeedControls.MAXIMUM_VALOCITY_BACKWARD.value:

            self._move_speed -= 1

            if self.websocket:
                try:
                    # Invia il nuovo valore della velocità tramite WebSocket ad ogni ciclo
                    await self.websocket.send(json.dumps({
                        "ok": True,
                        "motorspeed": self._move_speed,
                        "direction": "backward"
                    }))
                except Exception as e:
                    print(f"Errore durante l'invio dei dati al client: {e}")

            await asyncio.sleep(self._UPDATE_VELOCITY_TIME_OFFSET)

    async def stop(self) -> None:
        """
        Riduce gradualmente la velocità del motore fino a fermarlo completamente.

        La decelerazione è dinamica: più alta è la velocità attuale, più rapido è l'arresto iniziale.
        Man mano che la velocità diminuisce, il rallentamento diventa più dolce.
        L'intensità della frenata è modulata da `self._brake_intensity` (0-100), dove un valore più alto
        corrisponde a una frenata più rapida.

        Durante il processo, la nuova velocità viene inviata al client ad ogni variazione.

        Raises:
            Exception: se la connessione websocket viene chiusa inaspettatamente.
        """
        if self._move_speed == 0:
            return

        if not self._is_moving:
            return

        self._is_moving = False

        max_speed = abs(self._move_speed)
        brake_factor = min(self._brake_intensity, 100) / 100
        brake_factor = max(brake_factor, 0.05)

        while self._move_speed != 0:
            speed_ratio = abs(self._move_speed) / max_speed
            delay = self._UPDATE_VELOCITY_TIME_OFFSET + (0.6 * speed_ratio)
            delay *= (1 - brake_factor) ** 1.5

            if self._move_speed > 0:
                self._move_speed = max(0, self._move_speed - 1)
            else:
                self._move_speed = min(0, self._move_speed + 1)

            await self.websocket.send(json.dumps({
                "ok": True,
                "motorspeed": self._move_speed,
                "stopping": True
            }))

            await asyncio.sleep(delay)

        try:
            await self.websocket.send(json.dumps({
                "ok": True, "motorspeed": 0
            }))
        except websockets.exceptions.ConnectionClosedError as e:
            raise Exception from e

    def set_gear(self, value: str) -> None:
        """
        Imposta la marcia del veicolo.
        
        Args:
            value (str): La marcia da impostare. Le marce disponibili sono: "R, N, 1, 2, 3, 4"
        
        Returns:
            None.
        """
        self._motor_gear = value

    def set_turbo(self, value: int) -> None:
        """
        Imposta il valore del turbo tra 0 e 100.

        Args:
            value (int): Il valore da impostare come turbo.

        Returns:
            None.
        """
        mapped_value = round(value * 0.4) 
        self._turbo_value = mapped_value

    def set_brake_value(self, value: int) -> None:
        """
        Imposta il valore del freno tra 0 e 100.

        Args:
            value (int): Il valore da impostare come moltiplicatore del freno.

        Returns:
            None.
        """
        mapped_value = round(value * 0.4, 1) 
        self._brake_intensity = mapped_value


    


