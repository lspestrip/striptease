#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QMainWindow>
#include <QTimer>
#include "commandlist.hpp"
#include "stripconnection.hpp"

namespace Ui {
class MainWindow;
}

class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
    explicit MainWindow(QWidget *parent = nullptr);
    ~MainWindow();

    void loadJsonFile(const QString & fileName);
    void logMessage(const QString & msg);

private slots:
    void on_action_quit_triggered();
    void on_action_load_triggered();
    void on_command_timer_triggered();
    void on_command_success();
    void on_connection_error(const QString &);
    void on_runButton_clicked();
    void on_runNextButton_clicked();

    void on_action_set_delay_triggered();

    void on_addLogMessageButton_clicked();

    void on_action_reset_connection_triggered();

private:
    // Do *not* use std::unique_ptr here, as it confuses Qt Creator!
    Ui::MainWindow *ui;

    CommandList * commandList;
    QTimer * commandTimer;
    int delay_msec;
    StripConnection * connection;

    /* This points to an element in "commandList" when a POST request is sent
     * to the server, but before receiving the server's answer. Otherwise,
     * it is set to -1. */
    int currentCommandIdx;

    void setupConnection();
    void startTimer();
    void stopTimer();
    void updateProgressBar();
};

#endif // MAINWINDOW_H
