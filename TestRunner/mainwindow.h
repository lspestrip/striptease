#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QMainWindow>
#include <QTimer>
#include "commandlist.hpp"

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

private slots:
    void on_action_quit_triggered();
    void on_action_load_triggered();
    void on_command_timer_triggered();

    void on_runButton_clicked();

    void on_runNextButton_clicked();

private:
    // Do *not* use std::unique_ptr here, as it confuses Qt Creator!
    Ui::MainWindow *ui;

    CommandList * command_list;
    QTimer * command_timer;

    int delay_msec;
};

#endif // MAINWINDOW_H
