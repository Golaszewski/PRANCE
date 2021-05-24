/* Name: main.c
 * Author: <insert your name here>
 * Copyright: <insert your copyright message here>
 * License: <insert your license reference here>
 */

#include <avr/io.h>
#include "usi_i2c_slave.h"

//Define a reference to the I2C slave register bank pointer array
extern unsigned char* USI_Slave_register_buffer[2];
#define DRIVER_IN1_PIN 3 //PB3, chip pin 2
#define DRIVER_IN2_PIN 4 //PB4, chip pin 3
#define DRIVER_IN1_MASK (1 << DRIVER_IN1_PIN)
#define DRIVER_IN2_MASK (1 << DRIVER_IN2_PIN)
// what would be ENC_1_PIN is 5, PB5, ADC0, chip pin 1 (reset), set up in ADC below
#define ENC_2_PIN 1 //PB1, chip pin 6
#define ENC_2_MASK (1 << ENC_2_PIN)
#define COUNT_ERROR_MARGIN 5

void initADC() {
    /* this function initialises the ADC 
       ADC Prescaler Notes:
       --------------------
       ADC Prescaler needs to be set so that the ADC input frequency is between 50 - 200kHz.
       For more information, see table 17.5 "ADC Prescaler Selections" in 
       chapter 17.13.2 "ADCSRA – ADC Control and Status Register A"
       (pages 140 and 141 on the complete ATtiny25/45/85 datasheet, Rev. 2586M–AVR–07/10)
       Valid prescaler values for various clock speeds
       Clock   Available prescaler values
       ---------------------------------------
       1 MHz   8 (125kHz), 16 (62.5kHz)
       4 MHz   32 (125kHz), 64 (62.5kHz)
       8 MHz   64 (125kHz), 128 (62.5kHz)
       16 MHz   128 (125kHz)
       Below example set prescaler to 128 for mcu running at 8MHz
       (check the datasheet for the proper bit values to set the prescaler)
       */
    // 8-bit resolution
    // set ADLAR to 1 to enable the Left-shift result (only bits ADC9..ADC2 are available)
    // then, only reading ADCH is sufficient for 8-bit results (256 values)

    ADMUX =
        (1 << ADLAR) |     // left shift result
        (0 << REFS1) |     // Sets ref. voltage to VCC, bit 1
        (0 << REFS0) |     // Sets ref. voltage to VCC, bit 0
        (0 << MUX3)  |     // use ADC0 for input (PB5, reset), MUX bit 3
        (0 << MUX2)  |     // use ADC0 for input (PB5, reset), MUX bit 2
        (0 << MUX1)  |     // use ADC0 for input (PB5, reset), MUX bit 1
        (0 << MUX0);       // use ADC0 for input (PB5, reset), MUX bit 0
    ADCSRA = 
        (1 << ADEN)  |     // Enable ADC 
        (1 << ADPS2) |     // set prescaler to 64, bit 2 
        (1 << ADPS1) |     // set prescaler to 64, bit 1 
        (0 << ADPS0);      // set prescaler to 64, bit 0  
}

int enc1read(void) {
    ADCSRA |= (1 << ADSC);         // start ADC measurement
    while (ADCSRA & (1 << ADSC) ); // wait till conversion complete 
    if (ADCH > 230) {
        return 1;
    }
    return 0;
}

int enc2read(void) {
    if (PINB & ENC_2_MASK) {
        return 1;
    }
    return 0;
}



int main(void) {

    //Driver pins are outputs
    DDRB |= (DRIVER_IN1_MASK | DRIVER_IN2_MASK);

    initADC();

    volatile int enc_pos = 0;
    //Assign the encoder position low byte to I2C internal address 0x00
    //Assign the encoder position high byte to I2C internal address 0x01
    USI_Slave_register_buffer[0] = (unsigned char*)&enc_pos;
    USI_Slave_register_buffer[1] = (unsigned char*)(&enc_pos)+1;

    //Initialize I2C slave with slave device address /I2C_ADDR/
    //NOTE: DESIGNED TO BE REPLACED WITH SED
    USI_I2C_Init(/I2C_ADDR/);

    char state = 0;
    switch ((enc1read() << 1) + enc2read()) {
        case 3:
            state = 3;
            break;
        case 2:
            state = 2;
            break;
        case 1:
            state = 0;
            break;
        default:
            state = 1;
    }

    while(1) {
        if (enc1read()) {
            if (enc2read()) {
                if (state == 2) {
                    enc_pos++;
                } else if (state == 0) {
                    enc_pos--;
                }
                state = 3;
            } else {
                if (state == 1) {
                    enc_pos++;
                } else if (state == 3) {
                    enc_pos--;
                }
                state = 2;
            }
        } else {
            if (enc2read()) {
                if (state == 3) {
                    enc_pos++;
                } else if (state == 1) {
                    enc_pos--;
                }
                state = 0;
            } else {
                if (state == 0) {
                    enc_pos++;
                } else if (state == 2) {
                    enc_pos--;
                }
                state = 1;
            }
        }

        if (enc_pos < -COUNT_ERROR_MARGIN) {
            // Drive forward
            PORTB |= DRIVER_IN1_MASK;
            PORTB &= (~DRIVER_IN2_MASK);
        } else if (enc_pos > COUNT_ERROR_MARGIN) {
            // Drive backward
            PORTB |= DRIVER_IN2_MASK;
            PORTB &= (~DRIVER_IN1_MASK);
        } else {
            // Stop near 0
            PORTB &= (~(DRIVER_IN1_MASK | DRIVER_IN2_MASK));
        }

    }
    return 0;
}
